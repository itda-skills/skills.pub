#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stealth.py - 안티봇 탐지 JavaScript 패치 번들.

Cloudflare, Akamai 등 봇 탐지 시스템을 우회하기 위한 JavaScript 패치 모음.
각 패치는 독립 문자열로 관리되어 개별 활성화/비활성화가 가능하다.

SPEC: SPEC-WEBREADER-004 REQ-1.1~REQ-1.8
"""
from __future__ import annotations

# @MX:NOTE: [AUTO] 각 패치는 독립 문자열로 관리 — 패치별 활성화/비활성화 용이
# @MX:SPEC: SPEC-WEBREADER-004

STEALTH_VERSION = "1.0.0"

STEALTH_SCRIPTS: list[str] = [
    # REQ-1.2: navigator.webdriver → undefined
    # Selenium/Playwright 자동화 탐지에 사용되는 navigator.webdriver를 숨긴다
    """
Object.defineProperty(navigator, 'webdriver', {
  get: () => undefined,
  configurable: true
});
""",
    # REQ-1.3: window.chrome 객체 생성
    # Chrome 브라우저에서만 존재하는 window.chrome 객체를 생성한다
    """
if (!window.chrome) {
  Object.defineProperty(window, 'chrome', {
    value: {
      runtime: {
        onConnect: { addListener: function() {} },
        onMessage: { addListener: function() {} }
      },
      loadTimes: function() {},
      csi: function() {},
      app: {}
    },
    configurable: true,
    writable: true
  });
}
""",
    # REQ-1.4: Permissions API Promise<PermissionStatus> 계약 유지
    # permissions.query()가 state 프로퍼티를 가진 PermissionStatus 객체를 Promise로 반환하도록 패치
    # 중요: state: 'granted' 형태의 프로퍼티를 포함해야 봇 탐지를 우회할 수 있다
    """
(function() {
  if (navigator.permissions && navigator.permissions.query) {
    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = function(parameters) {
      if (parameters && parameters.name === 'notifications') {
        const proto = window.PermissionStatus ? window.PermissionStatus.prototype : Object.prototype;
        const statusObj = Object.assign(Object.create(proto), {
          state: (window.Notification && Notification.permission) || 'prompt',
          onchange: null
        });
        return Promise.resolve(statusObj);
      }
      try {
        return originalQuery(parameters);
      } catch (e) {
        const proto = window.PermissionStatus ? window.PermissionStatus.prototype : Object.prototype;
        return Promise.resolve(Object.assign(Object.create(proto), {
          state: 'prompt',
          onchange: null
        }));
      }
    };
  }
})();
""",
    # REQ-1.5: navigator.plugins 채우기 (비어있지 않은 PluginArray)
    # 빈 plugins 배열은 headless 브라우저 탐지에 사용되므로 PDF 플러그인을 추가한다
    """
(function() {
  const pluginData = [
    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', mimeType: { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' } },
    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', mimeType: { type: 'application/pdf', suffixes: 'pdf', description: '' } },
    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '', mimeType: { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' } }
  ];

  const pluginArr = pluginData.map(function(p) {
    const plugin = Object.create(Plugin.prototype);
    Object.defineProperty(plugin, 'name', { get: () => p.name });
    Object.defineProperty(plugin, 'filename', { get: () => p.filename });
    Object.defineProperty(plugin, 'description', { get: () => p.description });
    Object.defineProperty(plugin, 'length', { get: () => 1 });
    const mt = Object.create(MimeType.prototype);
    Object.defineProperty(mt, 'type', { get: () => p.mimeType.type });
    plugin[0] = mt;
    return plugin;
  });

  Object.defineProperty(navigator, 'plugins', {
    get: () => {
      const arr = Object.create(PluginArray.prototype);
      pluginArr.forEach(function(p, i) { arr[i] = p; });
      Object.defineProperty(arr, 'length', { get: () => pluginArr.length });
      arr.item = function(i) { return arr[i] || null; };
      arr.namedItem = function(name) {
        return pluginArr.find(function(p) { return p.name === name; }) || null;
      };
      arr.refresh = function() {};
      return arr;
    },
    configurable: true
  });
})();
""",
    # REQ-1.6: navigator.languages 일관성 (ko-KR, en-US 포함)
    # navigator.language와 navigator.languages가 일치하지 않으면 봇으로 탐지된다
    """
Object.defineProperty(navigator, 'language', {
  get: () => 'ko-KR',
  configurable: true
});
Object.defineProperty(navigator, 'languages', {
  get: () => ['ko-KR', 'ko', 'en-US', 'en'],
  configurable: true
});
""",
    # REQ-1.7: WebGL vendor/renderer 스푸핑
    # REQ-2.8: fetch_dynamic UA(Windows Chrome)와 일치하는 Windows WebGL 문자열 사용
    # headless Chrome에서 WebGL vendor가 실제 GPU가 아닌 'Google Inc.'로 표시되지 않는 문제를 수정
    # WebGLRenderingContext + WebGL2RenderingContext 양쪽 모두 패치
    """
(function() {
  var UNMASKED_VENDOR_WEBGL = 37445;
  var UNMASKED_RENDERER_WEBGL = 37446;
  var vendorStr = 'Google Inc. (Intel)';
  var rendererStr = 'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)';

  if (typeof WebGLRenderingContext !== 'undefined') {
    var getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
      if (parameter === UNMASKED_VENDOR_WEBGL) return vendorStr;
      if (parameter === UNMASKED_RENDERER_WEBGL) return rendererStr;
      return getParameter.apply(this, arguments);
    };
  }

  if (typeof WebGL2RenderingContext !== 'undefined') {
    var getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
      if (parameter === UNMASKED_VENDOR_WEBGL) return vendorStr;
      if (parameter === UNMASKED_RENDERER_WEBGL) return rendererStr;
      return getParameter2.apply(this, arguments);
    };
  }
})();
""",
]


def get_stealth_scripts() -> list[str]:
    """모든 스텔스 스크립트를 복사본으로 반환한다 (원본 불변성 보장).

    Returns:
        STEALTH_SCRIPTS의 복사본 list.
    """
    return list(STEALTH_SCRIPTS)


def apply_stealth(context: object) -> None:
    """모든 스텔스 패치를 Playwright context에 적용한다.

    Args:
        context: Playwright BrowserContext 또는 launch_persistent_context 반환값.
                 add_init_script() 메서드를 가져야 한다.
    """
    for script in STEALTH_SCRIPTS:
        context.add_init_script(script)  # type: ignore[union-attr]
