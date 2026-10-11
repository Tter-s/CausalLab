"use client";

/**
 * 仅开发环境挂载（见 layout.tsx）：增强 Next.js 内置 Dev Tools 面板。
 *
 * 1. 中文化：Next Dev Tools 渲染在 <nextjs-portal> 的 open shadow DOM 里，
 *    官方不提供 i18n；这里用「精确匹配文本节点替换」汉化菜单与子面板，
 *    MutationObserver 兜底——React 重渲染后自动重新应用。未收录的文案原样保留。
 * 2. 自由拖拽：面板定位由 Next 写死为 fixed+bottom/right，这里在其之上叠加
 *    transform 偏移（不修改 Next 自身样式），拖「N」按钮或面板均可整体移动，
 *    位置存 localStorage，双击「N」按钮复位。
 *
 * 说明：此处中文是开发工具汉化词典，不走应用 t() i18n（Vitest 覆盖扫描只针对 t() 调用）。
 * Next 升级若改变内部结构，本组件所有逻辑自动退化为「什么都不做」，不影响应用。
 */

import { useEffect } from "react";

const DEVTOOLS_TEXT_ZH: Record<string, string> = {
  // 主菜单
  Route: "路由",
  Static: "静态",
  Dynamic: "动态",
  Bundler: "打包器",
  "Route Info": "路由信息",
  Preferences: "偏好设置",
  // Route Info 面板
  "Clear Segment Overrides": "清除分段覆盖",
  // Preferences 面板
  Theme: "主题",
  "Select your theme preference.": "选择你的主题偏好。",
  System: "跟随系统",
  Light: "浅色",
  Dark: "深色",
  Position: "位置",
  "Adjust the placement of your dev tools.": "调整开发工具在页面上的位置。",
  "Bottom Left": "左下角",
  "Bottom Right": "右下角",
  "Top Left": "左上角",
  "Top Right": "右上角",
  Size: "大小",
  "Adjust the size of your dev tools.": "调整开发工具的大小。",
  Small: "小",
  Medium: "中",
  Large: "大",
  "Hide Dev Tools for this session": "本次会话隐藏开发工具",
  "Hide Dev Tools until you restart your dev server, or 1 day.":
    "隐藏开发工具，直到重启开发服务器或满 1 天。",
  Hide: "隐藏",
  "Hide Dev Tools shortcut": "开发工具显隐快捷键",
  "Set a custom keyboard shortcut to toggle visibility.": "设置切换显隐的自定义快捷键。",
  "Record Shortcut": "录制快捷键",
  "Disable Dev Tools for this project": "对本项目禁用开发工具",
  "To disable this UI completely, set devIndicators: false in your next.config file.":
    "如需彻底关闭此界面，请在 next.config 中设置 devIndicators: false。",
  "Restart Dev Server": "重启开发服务器",
  "Restarts the development server without needing to leave the browser.":
    "无需离开浏览器即可重启开发服务器。",
  Restart: "重启",
  "Reset Bundler Cache": "重置打包器缓存",
  "Clears the bundler cache and restarts the dev server. Helpful if you are seeing stale errors or changes are not appearing.":
    "清空打包器缓存并重启开发服务器。当报错信息过期或改动不生效时有用。",
  "Reset Cache": "重置缓存",
  // 状态与提示
  "Waiting for navigation...": "等待页面跳转…",
  "Navigation Inspector": "跳转检查器",
  "Loading...": "加载中…",
  Copied: "已复制",
  "Page load": "页面加载",
  "Learn more": "了解更多",
};

const DEVTOOLS_ATTR_ZH: Record<string, string> = {
  "Open Next.js Dev Tools": "打开 Next.js 开发工具（可拖动，双击复位）",
  "Close Next.js Dev Tools": "关闭 Next.js 开发工具",
};

const DRAG_STORE_KEY = "causalab-devtools-drag-offset";
const DRAG_THRESHOLD_PX = 4;

type Offset = { x: number; y: number };

function readOffset(): Offset {
  try {
    const raw = window.localStorage.getItem(DRAG_STORE_KEY);
    if (!raw) return { x: 0, y: 0 };
    const v = JSON.parse(raw) as Partial<Offset>;
    return { x: Number(v.x) || 0, y: Number(v.y) || 0 };
  } catch {
    return { x: 0, y: 0 };
  }
}

/** 汉化 root 下所有精确匹配的文本节点 */
function translateText(root: ParentNode) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const targets: Text[] = [];
  let node = walker.nextNode();
  while (node) {
    if (node.nodeType === Node.TEXT_NODE) targets.push(node as Text);
    node = walker.nextNode();
  }
  for (const t of targets) {
    const key = t.nodeValue?.trim();
    if (!key) continue;
    const zh = DEVTOOLS_TEXT_ZH[key];
    if (zh && t.nodeValue !== zh) t.nodeValue = zh;
  }
}

/** 汉化 aria-label / title 属性 */
function translateAttrs(root: ParentNode) {
  for (const el of root.querySelectorAll<HTMLElement>("[aria-label],[title]")) {
    for (const attr of ["aria-label", "title"] as const) {
      const zh = DEVTOOLS_ATTR_ZH[el.getAttribute(attr) ?? ""];
      if (zh) el.setAttribute(attr, zh);
    }
  }
}

/** 拖拽偏移作用于：N 按钮容器(.nextjs-toast) 与菜单/子面板的 fixed 祖先 */
function fixedContainers(sr: ShadowRoot): Element[] {
  const out: Element[] = [];
  const toast = sr.querySelector(".nextjs-toast");
  if (toast) out.push(toast);
  const menu = sr.querySelector('[role="menu"]');
  if (menu) {
    // 菜单卡片自身可能就是 fixed 元素（Next 16 结构），故从自身开始向上找
    let el: Element | null = menu;
    while (el) {
      if (getComputedStyle(el).position === "fixed") {
        out.push(el);
        break;
      }
      el = el.parentElement;
    }
  }
  return out;
}

export function DevToolsZh() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;

    const observedRoots = new WeakSet<ShadowRoot>();
    let raf = 0;
    let offset = readOffset();
    let drag: { x0: number; y0: number; baseX: number; baseY: number; moved: boolean } | null = null;
    let suppressClick = false;

    const applyOffset = () => {
      for (const portal of document.querySelectorAll("nextjs-portal")) {
        const sr = (portal as HTMLElement).shadowRoot;
        if (!sr) continue;
        for (const el of fixedContainers(sr)) {
          (el as HTMLElement).style.transform = `translate(${offset.x}px, ${offset.y}px)`;
        }
      }
    };

    const enhancePortal = (portal: Element) => {
      const sr = (portal as HTMLElement).shadowRoot;
      if (!sr || observedRoots.has(sr)) return;
      observedRoots.add(sr);
      translateText(sr);
      translateAttrs(sr);
      applyOffset();
      mo.observe(sr, { childList: true, subtree: true, characterData: true });
    };

    const mo = new MutationObserver(() => schedule());
    const docMo = new MutationObserver(() => schedule());

    const schedule = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        for (const portal of document.querySelectorAll("nextjs-portal")) enhancePortal(portal);
        // 面板开合会重建 DOM：重放文本汉化与拖拽偏移
        for (const portal of document.querySelectorAll("nextjs-portal")) {
          const sr = (portal as HTMLElement).shadowRoot;
          if (!sr) continue;
          translateText(sr);
          translateAttrs(sr);
        }
        applyOffset();
      });
    };

    // ---- 拖拽 ----
    const portalContainerOf = (e: Event): Element | null => {
      const path = e.composedPath();
      const portalIdx = path.findIndex(
        (n) => n instanceof Element && (n as Element).tagName === "NEXTJS-PORTAL",
      );
      if (portalIdx < 0) return null;
      for (let i = 0; i < portalIdx; i++) {
        const n = path[i];
        if (n instanceof Element && getComputedStyle(n).position === "fixed") return n;
      }
      return null;
    };

    const onPointerDown = (e: PointerEvent) => {
      if (e.button !== 0) return;
      if (!portalContainerOf(e)) return;
      drag = { x0: e.clientX, y0: e.clientY, baseX: offset.x, baseY: offset.y, moved: false };
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!drag) return;
      const dx = e.clientX - drag.x0;
      const dy = e.clientY - drag.y0;
      if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
      if (!drag.moved) {
        drag.moved = true;
        document.documentElement.style.userSelect = "none";
      }
      offset = { x: Math.round(drag.baseX + dx), y: Math.round(drag.baseY + dy) };
      applyOffset();
    };

    const onPointerUp = () => {
      if (!drag) return;
      if (drag.moved) {
        // 拖拽手势结束后拦截紧随的 click，避免误开/误关菜单
        suppressClick = true;
        try {
          window.localStorage.setItem(DRAG_STORE_KEY, JSON.stringify(offset));
        } catch {
          /* 隐私模式等场景下忽略持久化失败 */
        }
      }
      drag = null;
      document.documentElement.style.userSelect = "";
    };

    const onClickCapture = (e: MouseEvent) => {
      if (!suppressClick) return;
      suppressClick = false;
      e.stopPropagation();
      e.preventDefault();
    };

    const onDblClick = (e: MouseEvent) => {
      if (
        !e
          .composedPath()
          .some((n) => n instanceof Element && (n as Element).tagName === "NEXTJS-PORTAL")
      )
        return;
      offset = { x: 0, y: 0 };
      try {
        window.localStorage.removeItem(DRAG_STORE_KEY);
      } catch {
        /* 同上 */
      }
      applyOffset();
    };

    docMo.observe(document.documentElement, { childList: true, subtree: true });
    schedule();
    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("pointermove", onPointerMove, true);
    document.addEventListener("pointerup", onPointerUp, true);
    document.addEventListener("click", onClickCapture, true);
    document.addEventListener("dblclick", onDblClick, true);

    return () => {
      docMo.disconnect();
      mo.disconnect();
      if (raf) cancelAnimationFrame(raf);
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("pointermove", onPointerMove, true);
      document.removeEventListener("pointerup", onPointerUp, true);
      document.removeEventListener("click", onClickCapture, true);
      document.removeEventListener("dblclick", onDblClick, true);
      document.documentElement.style.userSelect = "";
    };
  }, []);

  return null;
}
