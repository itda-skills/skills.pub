"""CSS selector definitions for itda-web-reader content extraction.

Ported from Defuddle v0.13.0 (TypeScript) to Python.
"""
from __future__ import annotations

import re

# Entry point selectors for main content detection (priority order)
# More specific selectors come first; 'body' is the final fallback.
ENTRY_POINT_SELECTORS: list[str] = [
    "#post",
    ".post-content",
    ".post-body",
    ".article-content",
    "#article-content",
    ".article_post",
    ".article-wrapper",
    ".entry-content",
    ".content-article",
    ".instapaper_body",
    ".post",
    ".markdown-body",
    "article",
    '[role="article"]',
    "main",
    '[role="main"]',
    "#content",
    "body",
]

# Exact CSS selectors for element removal (~100 selectors)
EXACT_REMOVE_SELECTORS: list[str] = [
    # Inline scripts and styles
    "noscript",
    "script",
    "style",
    # Structural chrome
    "header",
    "footer",
    "nav",
    # Note: "form" intentionally excluded — ASP.NET WebForms sites (e.g. OhmyNews)
    # wrap the entire page body in <form runat="server">, so removing <form> destroys content.
    "button",
    "dialog",
    "aside",
    # Generic ad/promotional classes
    ".ad",
    ".ads",
    ".advert",
    ".advertisement",
    # Layout helpers
    ".sidebar",
    ".side-bar",
    ".widget",
    ".banner",
    # Overlays and popups
    ".popup",
    ".modal",
    ".overlay",
    # Marketing noise
    ".cookie",
    ".promo",
    ".promotion",
    ".newsletter",
    # Social sharing
    ".social",
    ".share",
    ".sharing",
    # Content discovery noise
    ".related",
    ".recommended",
    ".tags",
    ".tag-list",
    # Comment sections
    ".comments",
    ".comment-section",
    # Author info
    ".author-bio",
    ".author-info",
    ".byline",
    # Navigation aids
    ".breadcrumb",
    ".breadcrumbs",
    # Table of contents
    ".toc",
    ".table-of-contents",
    # Post meta
    ".meta",
    ".post-meta",
    # ID-based selectors
    "#sidebar",
    "#header",
    "#footer",
    "#nav",
    "#navigation",
    "#comments",
    "#disqus_thread",
    # Pagination
    ".wp-pagenavi",
    ".pagination",
    ".page-nav",
    ".nav-links",
    # ARIA roles for structural chrome
    '[role="banner"]',
    '[role="navigation"]',
    '[role="complementary"]',
    # ARIA ad labels
    '[aria-label="advertisement"]',
    # Data attributes for ads
    "[data-ad]",
    "[data-ads]",
]

# Compiled regex for partial class/ID pattern matching (~40 key patterns)
# Matches class/ID substrings that indicate non-content elements.
PARTIAL_REMOVE_PATTERNS: re.Pattern[str] = re.compile(
    r"(?i)\b(?:"
    r"advert"
    r"|article-meta"
    r"|author-bio"
    r"|breadcrumb"
    r"|byline"
    r"|caption-side"
    r"|comments"
    r"|cookie"
    r"|footer"
    r"|header-widget"
    r"|masthead"
    r"|more-articles"
    r"|navbar"
    r"|newsletter"
    r"|paid-content"
    r"|paywall"
    r"|promo"
    r"|recommended"
    r"|related"
    r"|right-rail"
    r"|rss"
    r"|share-btn"
    r"|sidebar"
    r"|skip-to"
    r"|social"
    r"|sponsored"
    r"|subscribe"
    r"|tag-list"
    r"|toolbar"
    r"|trending"
    r"|widget"
    r")\b"
)

# Compiled regex for content-indicating class/ID patterns
# Matches class/ID substrings that indicate main content elements.
CONTENT_CLASS_PATTERNS: re.Pattern[str] = re.compile(
    r"(?i)\b(?:"
    r"content"
    r"|article"
    r"|post"
    r"|entry"
    r"|blog"
    r"|story"
    r"|main"
    r"|body"
    r"|text"
    r"|prose"
    r"|markdown"
    r")\b"
)

# Compiled regex for navigation/non-content keyword patterns
NAV_KEYWORD_PATTERNS: re.Pattern[str] = re.compile(
    r"(?i)\b(?:"
    r"advertisement"
    r"|cookie"
    r"|footer"
    r"|menu"
    r"|newsletter"
    r"|popup"
    r"|promo"
    r"|sidebar"
    r"|social"
    r"|sponsor"
    r")\b"
)
