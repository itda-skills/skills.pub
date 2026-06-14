from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from importlib import resources
from pathlib import PurePosixPath

from .image import render_report_image
from .models import DocSpec, ReportBlock, ReportImage, ReportItem, ReportTable
from .profile import MIME_TYPE, VERSION_XML, ImageEntry, SpecProfile, xml_escape
from .rawzip import RawZipWriter
from .table import render_report_table
from .validator import validate_archive
from .writecontext import WriteContext


class HWPXReportError(Exception):
    pass


@dataclass
class ReportStyle:
    charPrIDRef: str = ""
    paraPrIDRef: str = ""
    borderFillIDRef: str = ""


@dataclass
class ReportTemplate:
    id: str
    header: bytes
    section: str
    manifest: dict
    styles: dict[str, ReportStyle]

    def style(self, name: str) -> ReportStyle:
        try:
            return self.styles[name]
        except KeyError as exc:
            raise HWPXReportError(f'hwpx report: style "{name}" is missing in template "{self.id}"') from exc


def build_report(template_id: str, spec: DocSpec) -> bytes:
    tmpl = load_report_template(template_id)
    validate_report_spec(spec)
    section, images = build_report_section_xml(tmpl, spec)
    data = package_report_hwpx(tmpl, section.encode(), spec, images)
    result = validate_archive(data)
    if not result.all_passed:
        failed = []
        for check in result.checks:
            if not check.passed:
                failed.append(f"{check.name}: {check.message}" if check.message else check.name)
        raise HWPXReportError("hwpx report: generated archive failed validation: " + "; ".join(failed))
    return data


def write_report_file(template_id: str, spec: DocSpec, output_path: str) -> None:
    if not output_path.strip():
        raise HWPXReportError("hwpx report: output path is required")
    from pathlib import Path

    Path(output_path).write_bytes(build_report(template_id, spec))


def load_report_template(template_id: str) -> ReportTemplate:
    template_id = template_id.strip() or "gov-report"
    clean = str(PurePosixPath(template_id))
    if clean != template_id or template_id.startswith(".") or "/" in template_id or "\\" in template_id:
        raise HWPXReportError(f'hwpx report: invalid template id "{template_id}"')

    base = resources.files("hwpx_report").joinpath("assets", "templates", template_id)

    def read_bytes(name: str) -> bytes:
        try:
            return base.joinpath(name).read_bytes()
        except FileNotFoundError as exc:
            raise HWPXReportError(f"hwpx report: load {template_id}/{name}: {exc}") from exc

    header = read_bytes("header.xml")
    section = read_bytes("section0.skel.xml").decode()
    manifest = json.loads(read_bytes("manifest.json").decode())
    if manifest.get("id") and manifest["id"] != template_id:
        raise HWPXReportError(
            f'hwpx report: manifest id "{manifest["id"]}" does not match template id "{template_id}"'
        )
    raw_styles = json.loads(read_bytes("style-map.json").decode())
    styles = {
        name: ReportStyle(
            charPrIDRef=str(data.get("charPrIDRef", "")),
            paraPrIDRef=str(data.get("paraPrIDRef", "")),
            borderFillIDRef=str(data.get("borderFillIDRef", "")),
        )
        for name, data in raw_styles.items()
    }
    tmpl = ReportTemplate(template_id, header, section, manifest, styles)
    validate_report_template(tmpl)
    return tmpl


def validate_report_template(tmpl: ReportTemplate) -> None:
    for name in ("heading", "heading_spacer", "body_box", "blank"):
        tmpl.style(name)
    ids = collect_report_header_ids(tmpl.header)
    for name, style in tmpl.styles.items():
        if style.charPrIDRef and style.charPrIDRef not in ids["charPr"]:
            raise HWPXReportError(f'hwpx report: style "{name}" references missing charPrIDRef {style.charPrIDRef}')
        if style.paraPrIDRef and style.paraPrIDRef not in ids["paraPr"]:
            raise HWPXReportError(f'hwpx report: style "{name}" references missing paraPrIDRef {style.paraPrIDRef}')
        if style.borderFillIDRef and style.borderFillIDRef not in ids["borderFill"]:
            raise HWPXReportError(
                f'hwpx report: style "{name}" references missing borderFillIDRef {style.borderFillIDRef}'
            )


def collect_report_header_ids(header: bytes) -> dict[str, set[str]]:
    ids = {"charPr": set(), "paraPr": set(), "borderFill": set()}
    root = ET.fromstring(header)
    for el in root.iter():
        local = _local_name(el.tag)
        if local in ids and el.attrib.get("id"):
            ids[local].add(el.attrib["id"])
    return ids


def validate_report_spec(spec: DocSpec) -> None:
    for si, section in enumerate(spec.sections):
        for ii, item in enumerate(section.items):
            validate_report_item(item, f"sections[{si}].items[{ii}]")
        for ti, table in enumerate(section.tables):
            validate_report_table(table, f"sections[{si}].tables[{ti}]")
        for bi, block in enumerate(section.blocks):
            path = f"sections[{si}].blocks[{bi}]"
            validate_report_block(block, path)
    for ti, table in enumerate(spec.tables):
        validate_report_table(table, f"tables[{ti}]")


def validate_report_block(block: ReportBlock, path: str) -> None:
    set_count = sum(value is not None for value in (block.item, block.table, block.image))
    if set_count > 1:
        raise HWPXReportError(f"hwpx report: {path} must set exactly one of item/table/image")
    if block.item is not None:
        validate_report_item(block.item, f"{path}.item")
    elif block.table is not None:
        validate_report_table(block.table, f"{path}.table")
    elif block.image is not None:
        validate_report_image(block.image, f"{path}.image")
    else:
        raise HWPXReportError(f"hwpx report: {path} must set one of item/table/image")


def validate_report_image(image: ReportImage, path: str) -> None:
    if not image.src.strip():
        raise HWPXReportError(f"hwpx report: {path}.src is required")


def validate_report_item(item: ReportItem, path: str) -> None:
    if item.level not in (1, 2):
        raise HWPXReportError(f"hwpx report: {path}.level must be 1 or 2")
    if not item.text.strip():
        raise HWPXReportError(f"hwpx report: {path}.text is required")


def validate_report_table(table: ReportTable, path: str) -> None:
    if not table.headers:
        raise HWPXReportError(f"hwpx report: {path}.headers must not be empty")
    for ri, row in enumerate(table.rows):
        if len(row) != len(table.headers):
            raise HWPXReportError(f"hwpx report: {path}.rows[{ri}] has {len(row)} cells, want {len(table.headers)}")
    if table.aligns:
        if len(table.aligns) != len(table.headers):
            raise HWPXReportError(f"hwpx report: {path}.aligns has {len(table.aligns)} entries, want {len(table.headers)}")
        for ci, align in enumerate(table.aligns):
            if align.strip().lower() not in {"", "none", "left", "right", "center"}:
                raise HWPXReportError(f'hwpx report: {path}.aligns[{ci}] "{align}" must be left|right|center|none')
    if table.rich_rows:
        if len(table.rich_rows) != len(table.rows):
            raise HWPXReportError(
                f"hwpx report: {path}.rich_rows has {len(table.rich_rows)} rows, want {len(table.rows)}"
            )
        for ri, rich_row in enumerate(table.rich_rows):
            if len(rich_row) != len(table.headers):
                raise HWPXReportError(
                    f"hwpx report: {path}.rich_rows[{ri}] has {len(rich_row)} cells, want {len(table.headers)}"
                )
    if table.col_widths:
        if len(table.col_widths) != len(table.headers):
            raise HWPXReportError(
                f"hwpx report: {path}.col_widths has {len(table.col_widths)} entries, want {len(table.headers)}"
            )
        for ci, width in enumerate(table.col_widths):
            if width <= 0:
                raise HWPXReportError(f"hwpx report: {path}.col_widths[{ci}] {width} must be positive")


def build_report_section_xml(tmpl: ReportTemplate, spec: DocSpec) -> tuple[str, list[ImageEntry]]:
    section = replace_report_placeholders(tmpl.section, spec)
    body, images = build_report_body_xml(tmpl, spec)
    if not body:
        return section, images
    close_idx = section.rfind("</hs:sec>")
    if close_idx < 0:
        raise HWPXReportError("hwpx report: section skeleton missing </hs:sec>")
    return section[:close_idx] + body + section[close_idx:], images


def replace_report_placeholders(section: str, spec: DocSpec) -> str:
    title = spec.title.strip() or "보고자료 제목"
    report_date = normalize_report_date(spec.report_date)
    year2, date_suffix = split_report_date_for_template(report_date)
    dept = spec.dept.strip() or "부서명"
    replacements = [
        (". MM. DD., 부서명)", f"{date_suffix}, {dept})"),
        ("YY", year2),
        ("보고자료 제목", title),
    ]
    for token, value in replacements:
        section = section.replace(token, xml_escape(value))
    return section


def normalize_report_date(value: str) -> str:
    value = value.strip()
    if value:
        parsed = parse_report_date(value)
        return format_report_date(parsed) if parsed else value
    return format_report_date(date.today())


def parse_report_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y. %m. %d.", "%y. %m. %d.", "%Y.%m.%d.", "%y.%m.%d."):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def format_report_date(value: date) -> str:
    return f"{value.year % 100:02d}. {value.month}. {value.day}."


def split_report_date_for_template(value: str) -> tuple[str, str]:
    parts = value.strip().split(".", 1)
    if len(parts) != 2:
        now = date.today()
        return f"{now.year % 100:02d}", ". " + value.strip()
    year = parts[0].strip()
    if len(year) >= 2:
        year = year[-2:]
    return year, "." + parts[1]


def build_report_body_xml(tmpl: ReportTemplate, spec: DocSpec) -> tuple[str, list[ImageEntry]]:
    heading_style = tmpl.style("heading")
    spacer_style = tmpl.style("heading_spacer")
    body_style = tmpl.style("body_box")
    blank_style = tmpl.style("blank")

    ctx = WriteContext()
    images: list[ImageEntry] = []
    img_idx = 1
    parts: list[str] = []
    for index, section in enumerate(spec.sections):
        heading = section.heading.strip()
        has_body = bool(section.items or section.blocks)
        if heading:
            parts.append(append_report_paragraph(ctx, heading_style, heading))
            if has_body:
                parts.append(append_report_paragraph(ctx, spacer_style, ""))
        if section.blocks:
            for block in section.blocks:
                if block.item is not None:
                    parts.append(append_report_paragraph(ctx, body_style, format_report_item_text(block.item)))
                elif block.table is not None:
                    parts.append(_render_table(ctx, block.table, tmpl))
                elif block.image is not None:
                    rendered, entry = _render_image(ctx, block.image, img_idx, body_style.charPrIDRef)
                    img_idx += 1
                    images.append(entry)
                    parts.append(rendered)
        else:
            for item in section.items:
                parts.append(append_report_paragraph(ctx, body_style, format_report_item_text(item)))
            for table in section.tables:
                parts.append(_render_table(ctx, table, tmpl))
        if index < len(spec.sections) - 1:
            parts.append(append_report_paragraph(ctx, blank_style, ""))
    for table in spec.tables:
        parts.append(_render_table(ctx, table, tmpl))
    return "".join(parts), images


def _render_table(ctx: WriteContext, table: ReportTable, tmpl: ReportTemplate) -> str:
    try:
        return render_report_table(ctx, table, tmpl)
    except FileNotFoundError as exc:
        raise HWPXReportError(str(exc)) from exc
    except NotImplementedError as exc:
        raise HWPXReportError(str(exc)) from exc


def _render_image(ctx: WriteContext, image: ReportImage, img_idx: int, char_pr_id_ref: str) -> tuple[str, ImageEntry]:
    try:
        return render_report_image(ctx, image, img_idx, char_pr_id_ref)
    except OSError as exc:
        raise HWPXReportError(str(exc)) from exc
    except NotImplementedError as exc:
        raise HWPXReportError(str(exc)) from exc


def append_report_paragraph(ctx: WriteContext, style: ReportStyle, text: str) -> str:
    return (
        f'<hp:p id="{ctx.paragraph_id()}" styleIDRef="0" paraPrIDRef="{xml_escape(style.paraPrIDRef)}" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{xml_escape(style.charPrIDRef)}"><hp:t>{xml_escape(text)}</hp:t></hp:run>'
        "</hp:p>"
    )


def format_report_item_text(item: ReportItem) -> str:
    text = item.text.strip()
    if item.level == 1:
        return text if text.startswith("□") else "□ " + text
    if item.level == 2:
        left_trimmed = text.lstrip(" \t")
        return "  " + left_trimmed if left_trimmed.startswith("❍") else "  ❍ " + text
    return text


def package_report_hwpx(tmpl: ReportTemplate, section: bytes, spec: DocSpec, images: list[ImageEntry]) -> bytes:
    zw = RawZipWriter()
    profile = SpecProfile()
    zw.add_store("mimetype", MIME_TYPE.encode())
    zw.add_deflate("Contents/header.xml", tmpl.header)
    zw.add_deflate("Contents/section0.xml", section)
    zw.add_deflate("version.xml", VERSION_XML.encode())
    zw.add_deflate("Contents/content.hpf", profile.build_content_hpf(images, 1, spec.title, "hyve.hwpx.report"))
    zw.add_deflate("settings.xml", profile.build_settings_xml())
    zw.add_deflate("Preview/PrvText.txt", build_report_preview_text(spec))
    zw.add_deflate("META-INF/container.xml", profile.build_container_xml())
    zw.add_deflate("META-INF/manifest.xml", profile.build_manifest_xml())
    zw.add_deflate("META-INF/container.rdf", profile.build_container_rdf())
    for image in images:
        zw.add_store(image.href, image.data)
    return zw.finish()


def build_report_preview_text(spec: DocSpec) -> bytes:
    lines: list[str] = []
    if spec.title.strip():
        lines.append(spec.title.strip())
    for section in spec.sections:
        if section.heading.strip():
            lines.append(section.heading.strip())
        if section.blocks:
            for block in section.blocks:
                if block.item is not None:
                    lines.append(format_report_item_text(block.item))
        else:
            for item in section.items:
                lines.append(format_report_item_text(item))
    text = "\n".join(lines).strip() or "Document"
    return (text + "\n").encode()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
