#!/usr/bin/env python3
"""
Pacdora 刀版详情页深度抓取 — 聚焦 3D/2D 关系数据
=================================================
目标: https://www.pacdora.cn/dielines
策略:
  Phase 1 — 列表页: 滚动加载全部刀版卡片, 提取分类/链接/缩略图
  Phase 2 — 详情页(采样): 拦截 demoProject JSON (3D几何+材质+UV), 
            提取 2D SVG 刀线, 尺寸参数面板, 3D↔2D 面板映射关系
  Phase 3 — 结构化输出: JSON + 分析报告

关键发现(前序分析):
  - demoProject JSON URL: https://cloud.pacdora.com/demoProject/{num}.json
  - 包含: 面板几何(vertices/faces), UV映射, 材质贴图URL, 折叠角度
  - 详情页 nameKey 格式: custom-dimensions-{desc}-dieline-{num}
"""

import json
import time
import random
import re
import os
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

# ─── 配置 ─────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "pacdora_scrape_output"
OUTPUT_DIR.mkdir(exist_ok=True)

LISTING_URL = "https://www.pacdora.cn/dielines"
MAX_DETAIL_PAGES = 25          # 采样详情页数量(避免过量请求)
SCROLL_PAUSE_MIN = 1.5         # 滚动间隔(秒)
SCROLL_PAUSE_MAX = 3.0
DETAIL_WAIT_SEC = 6            # 详情页等待 3D 加载
REQUEST_DELAY = (2.0, 4.5)     # 页面间延迟

# 已有的模型 JSON(用于交叉验证)
MODELS_JSON = Path("/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json")


def human_delay(lo=1.0, hi=2.5):
    time.sleep(random.uniform(lo, hi))


def random_mouse(page, n=3):
    """模拟随机鼠标移动"""
    for _ in range(n):
        x = random.randint(200, 1600)
        y = random.randint(100, 800)
        page.mouse.move(x, y, steps=random.randint(5, 15))
        time.sleep(random.uniform(0.1, 0.3))


# ═══════════════════════════════════════════════════════════════
# Phase 1: 列表页 — 滚动加载全部刀版卡片
# ═══════════════════════════════════════════════════════════════

def scrape_listing(page) -> list:
    """抓取 /dielines 列表页全部卡片"""
    print("\n" + "=" * 60)
    print("Phase 1: 刀版列表页抓取")
    print("=" * 60)

    page.goto(LISTING_URL, wait_until="domcontentloaded", timeout=30000)
    human_delay(3, 5)

    # 等待卡片容器出现
    try:
        page.wait_for_selector("a[href*='dielines-detail']", timeout=15000)
        print("✅ 检测到刀版卡片链接")
    except PwTimeout:
        print("⚠️ 未检测到卡片链接, 尝试继续滚动...")

    # 滚动加载全部内容(懒加载)
    prev_count = 0
    stale_rounds = 0
    for i in range(30):  # 最多滚 30 轮
        random_mouse(page)
        scroll_dist = random.randint(800, 1500)
        page.evaluate(f"window.scrollBy(0, {scroll_dist})")
        human_delay(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX)

        # 偶尔小幅回滚(更自然)
        if i % 4 == 2:
            page.evaluate("window.scrollBy(0, -300)")
            human_delay(0.5, 1.0)

        # 计数当前卡片
        cards = page.query_selector_all("a[href*='dielines-detail']")
        count = len(cards)
        print(f"  滚动 #{i+1}: 已加载 {count} 个刀版卡片", end="\r")

        if count == prev_count:
            stale_rounds += 1
            if stale_rounds >= 4:
                print(f"\n  连续 {stale_rounds} 轮无新内容, 停止滚动")
                break
        else:
            stale_rounds = 0
        prev_count = count

    # 提取全部卡片数据
    cards = page.query_selector_all("a[href*='dielines-detail']")
    print(f"\n✅ 共发现 {len(cards)} 个刀版卡片链接")

    card_data = []
    seen_hrefs = set()
    for card in cards:
        try:
            href = card.get_attribute("href") or ""
            if href in seen_hrefs or "dielines-detail" not in href:
                continue
            seen_hrefs.add(href)

            # 提取卡片内文本和图片
            text = (card.text_content() or "").strip()[:200]
            img = card.query_selector("img")
            img_src = img.get_attribute("src") if img else None

            # 从 href 提取 num (末尾数字)
            num_match = re.search(r'-(\d{5,7})$', href)
            num = num_match.group(1) if num_match else None

            card_data.append({
                "href": href,
                "full_url": f"https://www.pacdora.cn{href}" if href.startswith("/") else href,
                "num": num,
                "text": text,
                "thumbnail": img_src,
            })
        except Exception as e:
            continue

    print(f"✅ 去重后 {len(card_data)} 个独立刀版")

    # 尝试提取分类导航
    categories = []
    try:
        cat_els = page.query_selector_all("[class*='category'], [class*='filter'], [class*='tag'], [class*='nav'] a")
        for el in cat_els[:50]:
            t = (el.text_content() or "").strip()
            h = el.get_attribute("href") or ""
            if t and len(t) < 50:
                categories.append({"text": t, "href": h})
    except:
        pass
    if categories:
        print(f"✅ 提取到 {len(categories)} 个分类/筛选项")

    return card_data


# ═══════════════════════════════════════════════════════════════
# Phase 2: 详情页 — 拦截 3D 数据 + 提取 2D/参数面板
# ═══════════════════════════════════════════════════════════════

def scrape_detail(page, url: str, num: str) -> dict:
    """
    抓取单个详情页:
    1. 拦截 demoProject JSON (3D 几何核心数据)
    2. 提取页面 DOM: 尺寸参数、材质选项、2D SVG
    3. 分析 3D Canvas 状态
    """
    result = {
        "url": url,
        "num": num,
        "demo_project": None,          # 拦截到的 3D 数据
        "intercepted_resources": [],    # 其他关键资源
        "page_title": None,
        "dimensions_panel": None,       # 尺寸参数面板
        "material_options": [],         # 材质选项
        "canvas_info": None,            # 3D Canvas 状态
        "svg_dieline": None,            # 2D 刀线 SVG
        "panel_mapping": None,          # 面板名称列表 (3D↔2D映射线索)
        "breadcrumb": None,             # 面包屑(分类信息)
        "download_options": [],         # 下载选项
        "related_items": [],            # 相关推荐
        "error": None,
    }

    # 拦截网络请求: 捕获 demoProject JSON + 纹理/模型资源
    captured = {"demo_json": None, "resources": []}

    def on_response(response):
        url_str = response.url
        try:
            # 核心: demoProject JSON
            if "demoProject" in url_str and url_str.endswith(".json"):
                if response.status == 200:
                    captured["demo_json"] = response.json()
                    print(f"    🎯 拦截到 demoProject JSON: {url_str}")

            # 纹理/模型资源
            elif any(ext in url_str for ext in [".glb", ".gltf", ".obj", ".fbx", ".hdr", ".ktx"]):
                captured["resources"].append({
                    "url": url_str,
                    "type": "3d_model",
                    "status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                })

            # SVG 刀线资源
            elif url_str.endswith(".svg") and ("dieline" in url_str.lower() or "die" in url_str.lower()):
                captured["resources"].append({
                    "url": url_str,
                    "type": "svg_dieline",
                    "status": response.status,
                })

            # 其他 API 调用
            elif "/api/" in url_str and response.status == 200:
                captured["resources"].append({
                    "url": url_str,
                    "type": "api_call",
                    "status": response.status,
                })
        except:
            pass

    page.on("response", on_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        human_delay(2, 3)

        # 等待 3D Canvas 加载
        try:
            page.wait_for_selector("canvas", timeout=12000)
            human_delay(DETAIL_WAIT_SEC - 2, DETAIL_WAIT_SEC)
            print(f"    ✅ Canvas 已加载")
        except PwTimeout:
            print(f"    ⚠️ Canvas 超时, 继续提取 DOM")
            human_delay(3, 4)

        # 模拟交互: 滚动 + 鼠标移动(触发懒加载组件)
        random_mouse(page, 4)
        page.evaluate("window.scrollBy(0, 600)")
        human_delay(1.5, 2.5)
        page.evaluate("window.scrollBy(0, 600)")
        human_delay(1.5, 2.5)

        # ── 提取页面标题
        result["page_title"] = page.title()

        # ── 提取面包屑
        try:
            bc_els = page.query_selector_all("[class*='breadcrumb'] a, [class*='Breadcrumb'] a, nav a")
            result["breadcrumb"] = [(el.text_content() or "").strip() for el in bc_els[:5] if el.text_content()]
        except:
            pass

        # ── 提取尺寸参数面板 (Pacdora 的可调节参数区)
        result["dimensions_panel"] = _extract_dimension_panel(page)

        # ── 提取材质选项
        result["material_options"] = _extract_material_options(page)

        # ── 提取 Canvas 3D 信息
        result["canvas_info"] = _extract_canvas_info(page)

        # ── 提取 2D 刀线 SVG
        result["svg_dieline"] = _extract_svg_dieline(page)

        # ── 提取面板映射关系 (核心: 3D↔2D)
        result["panel_mapping"] = _extract_panel_mapping(page)

        # ── 下载选项
        result["download_options"] = _extract_download_options(page)

        # ── 相关推荐
        try:
            related = page.query_selector_all("a[href*='dielines-detail']")
            for r in related[:10]:
                rh = r.get_attribute("href") or ""
                rt = (r.text_content() or "").strip()[:100]
                if rh and rh != url:
                    result["related_items"].append({"href": rh, "text": rt})
        except:
            pass

        # 赋值拦截数据
        result["demo_project"] = captured["demo_json"]
        result["intercepted_resources"] = captured["resources"]

    except Exception as e:
        result["error"] = str(e)
        print(f"    ❌ 错误: {e}")
    finally:
        page.remove_listener("response", on_response)

    return result


def _extract_dimension_panel(page) -> Optional[dict]:
    """提取尺寸参数面板: 长/宽/高输入框及其值"""
    try:
        # 尝试多种选择器(Pacdora 使用 Vue, class 名可能带 hash)
        dim_data = page.evaluate("""() => {
            const result = { inputs: [], labels: [], sliders: [] };
            
            // 数字输入框
            document.querySelectorAll('input[type="number"], input[type="text"]').forEach(inp => {
                const label = inp.closest('label')?.textContent?.trim() 
                    || inp.getAttribute('placeholder') 
                    || inp.getAttribute('aria-label')
                    || '';
                result.inputs.push({
                    value: inp.value,
                    label: label.slice(0, 50),
                    name: inp.name || '',
                    id: inp.id || '',
                    min: inp.min || null,
                    max: inp.max || null,
                    step: inp.step || null,
                });
            });
            
            // 含尺寸关键词的文本节点
            const dimKeywords = ['长', '宽', '高', 'length', 'width', 'height', 'depth',
                                 'mm', 'cm', '尺寸', 'dimension', 'size'];
            document.querySelectorAll('span, label, p, div').forEach(el => {
                const t = el.textContent?.trim() || '';
                if (t.length < 80 && dimKeywords.some(k => t.toLowerCase().includes(k))) {
                    result.labels.push(t);
                }
            });
            
            // 滑块
            document.querySelectorAll('input[type="range"]').forEach(sl => {
                result.sliders.push({
                    value: sl.value, min: sl.min, max: sl.max, step: sl.step,
                    label: sl.getAttribute('aria-label') || '',
                });
            });
            
            return result;
        }""")
        return dim_data if (dim_data.get("inputs") or dim_data.get("labels")) else None
    except:
        return None


def _extract_material_options(page) -> list:
    """提取材质选项(下拉/按钮组)"""
    try:
        mats = page.evaluate("""() => {
            const result = [];
            // 材质相关选择器
            document.querySelectorAll('select option, [class*="material"] *, [class*="paper"] *').forEach(el => {
                const t = el.textContent?.trim();
                if (t && t.length < 60 && !result.includes(t)) result.push(t);
            });
            // 也查找图片 alt 含 material/paper
            document.querySelectorAll('img[alt]').forEach(img => {
                const a = img.alt.trim();
                if ((a.includes('材') || a.includes('纸') || a.includes('paper') || a.includes('material'))
                    && a.length < 60) result.push(a);
            });
            return [...new Set(result)].slice(0, 30);
        }""")
        return mats
    except:
        return []


def _extract_canvas_info(page) -> Optional[dict]:
    """提取 3D Canvas 状态: 尺寸、WebGL 信息"""
    try:
        info = page.evaluate("""() => {
            const canvases = document.querySelectorAll('canvas');
            if (!canvases.length) return null;
            const results = [];
            canvases.forEach((c, i) => {
                const ctx = c.getContext('webgl2') || c.getContext('webgl');
                results.push({
                    index: i,
                    width: c.width,
                    height: c.height,
                    clientWidth: c.clientWidth,
                    clientHeight: c.clientHeight,
                    hasWebGL: !!ctx,
                    renderer: ctx ? ctx.getParameter(ctx.RENDERER) : null,
                    parentClass: c.parentElement?.className?.slice(0, 80) || '',
                });
            });
            return results;
        }""")
        return info
    except:
        return None


def _extract_svg_dieline(page) -> Optional[dict]:
    """提取 2D 刀线 SVG 或 Canvas 2D 元素"""
    try:
        svg_data = page.evaluate("""() => {
            // 直接嵌入的 SVG
            const svgs = document.querySelectorAll('svg');
            const dieline_svgs = [];
            svgs.forEach(svg => {
                const paths = svg.querySelectorAll('path, line, polyline, polygon, rect');
                if (paths.length > 5) {  // 至少5个元素才可能是刀线图
                    const viewBox = svg.getAttribute('viewBox') || '';
                    dieline_svgs.push({
                        viewBox: viewBox,
                        width: svg.getAttribute('width') || svg.clientWidth,
                        height: svg.getAttribute('height') || svg.clientHeight,
                        pathCount: paths.length,
                        // 提取前几个 path 的 d 属性 (刀线几何)
                        samplePaths: Array.from(paths).slice(0, 8).map(p => ({
                            tag: p.tagName,
                            d: p.getAttribute('d')?.slice(0, 200) || '',
                            stroke: p.getAttribute('stroke') || window.getComputedStyle(p).stroke || '',
                            strokeDasharray: p.getAttribute('stroke-dasharray') || '',
                            class: p.className?.baseVal?.slice(0, 50) || '',
                        })),
                        // 颜色分组 (cut=红, crease=蓝/虚线 通常)
                        strokeColors: [...new Set(
                            Array.from(paths).map(p => p.getAttribute('stroke') || 
                                window.getComputedStyle(p).stroke).filter(Boolean)
                        )].slice(0, 10),
                    });
                }
            });
            
            // 也检查 img 标签中的 SVG 引用
            const svgImgs = [];
            document.querySelectorAll('img[src*=".svg"]').forEach(img => {
                svgImgs.push({ src: img.src, alt: img.alt || '', width: img.width, height: img.height });
            });
            
            return {
                embedded_svgs: dieline_svgs,
                svg_images: svgImgs,
                total_svg_elements: svgs.length,
            };
        }""")
        return svg_data
    except:
        return None


def _extract_panel_mapping(page) -> Optional[dict]:
    """
    提取面板名称映射 — 3D↔2D 关系的关键线索
    Pacdora 通常在 demoProject JSON 中定义面板(face/back/left/right/top/bottom),
    这些面板同时出现在 2D 展开图和 3D 折叠模型中
    """
    try:
        mapping = page.evaluate("""() => {
            const data = { panel_labels: [], tab_labels: [], vue_data: null };
            
            // 面板标签 (常见: 正面/背面/侧面/顶面/底面)
            const panelKw = ['正面', '背面', '侧面', '顶', '底', '前', '后', '左', '右',
                             'front', 'back', 'side', 'top', 'bottom', 'left', 'right',
                             'face', 'panel', 'flap', 'lid'];
            document.querySelectorAll('span, div, button, label, li, a').forEach(el => {
                const t = el.textContent?.trim();
                if (t && t.length < 40 && panelKw.some(k => t.toLowerCase().includes(k))) {
                    data.panel_labels.push(t);
                }
            });
            data.panel_labels = [...new Set(data.panel_labels)].slice(0, 20);
            
            // Tab 标签 (2D/3D 切换)
            document.querySelectorAll('[class*="tab"], [role="tab"], [class*="switch"]').forEach(el => {
                const t = el.textContent?.trim();
                if (t && t.length < 30) data.tab_labels.push(t);
            });
            data.tab_labels = [...new Set(data.tab_labels)];
            
            // 尝试读取 Vue 组件 __vue__ 数据 (Chrome DevTools 风格)
            try {
                const app = document.querySelector('#app') || document.querySelector('[data-v-app]');
                if (app && app.__vue_app__) {
                    const rootData = app.__vue_app__.config?.globalProperties;
                    data.vue_data = { hasVueApp: true };
                }
            } catch(e) {}
            
            return data;
        }""")
        return mapping
    except:
        return None


def _extract_download_options(page) -> list:
    """提取下载选项"""
    try:
        opts = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('a[download], button, a').forEach(el => {
                const t = el.textContent?.trim() || '';
                const h = el.getAttribute('href') || '';
                if ((t.includes('下载') || t.includes('download') || t.includes('导出') || t.includes('export')
                     || t.includes('DXF') || t.includes('PDF') || t.includes('SVG') || t.includes('AI'))
                    && t.length < 60) {
                    results.push({ text: t, href: h.slice(0, 200) });
                }
            });
            return [...new Set(results.map(JSON.stringify))].map(JSON.parse).slice(0, 15);
        }""")
        return opts
    except:
        return []


# ═══════════════════════════════════════════════════════════════
# Phase 3: 分析 demoProject JSON — 3D↔2D 映射解构
# ═══════════════════════════════════════════════════════════════

def analyze_demo_project(demo: dict, num: str) -> dict:
    """深度解析 demoProject JSON, 提取 3D/2D 映射关系"""
    analysis = {
        "num": num,
        "panels": [],           # 面板列表 (3D几何 + 2D位置)
        "textures": [],         # 纹理贴图
        "materials": [],        # 材质参数
        "fold_angles": [],      # 折叠角度
        "geometry_summary": {}, # 几何概要
        "uv_mapping": None,     # UV映射信息 (2D→3D核心)
        "dimensions": {},       # 可调尺寸
    }

    if not demo:
        return analysis

    # demoProject 结构因版本不同, 尝试多种路径
    # 常见顶层 key: model, sizes, material, pages, background...
    top_keys = list(demo.keys())
    analysis["geometry_summary"]["top_keys"] = top_keys

    # 面板/pages (每个page = 一个可设计面)
    pages = demo.get("pages") or demo.get("panels") or demo.get("faces") or []
    if isinstance(pages, list):
        for pg in pages[:20]:
            panel = {
                "name": pg.get("name", pg.get("title", "")),
                "id": pg.get("id", ""),
                "width": pg.get("width"),
                "height": pg.get("height"),
                "visible": pg.get("visible", True),
                "printable": pg.get("printable"),
            }
            analysis["panels"].append(panel)

    # sizes (可调尺寸参数)
    sizes = demo.get("sizes") or demo.get("dimensions") or {}
    if isinstance(sizes, dict):
        analysis["dimensions"] = {k: v for k, v in sizes.items()
                                  if isinstance(v, (int, float, str))}
    elif isinstance(sizes, list):
        for s in sizes:
            if isinstance(s, dict):
                analysis["dimensions"][s.get("name", s.get("key", "?"))] = s.get("value", s)

    # material
    mat = demo.get("material") or demo.get("modeSetting") or {}
    if isinstance(mat, dict):
        analysis["materials"].append({
            k: (v if not isinstance(v, str) or len(v) < 200 else v[:200] + "...")
            for k, v in mat.items()
        })
    elif isinstance(mat, list):
        for m in mat[:5]:
            if isinstance(m, dict):
                analysis["materials"].append({
                    k: (v if not isinstance(v, str) or len(v) < 200 else v[:200] + "...")
                    for k, v in m.items()
                })

    # model (3D 几何)
    model = demo.get("model") or demo.get("geometry") or demo.get("mesh") or {}
    if isinstance(model, dict):
        analysis["geometry_summary"]["model_keys"] = list(model.keys())[:20]
        # 顶点/面数
        verts = model.get("vertices") or model.get("positions") or []
        faces = model.get("faces") or model.get("indices") or []
        analysis["geometry_summary"]["vertex_count"] = len(verts) if isinstance(verts, list) else "?"
        analysis["geometry_summary"]["face_count"] = len(faces) if isinstance(faces, list) else "?"

    # 折叠信息
    fold = demo.get("fold") or demo.get("foldAngle") or demo.get("animation") or {}
    if fold:
        analysis["fold_angles"] = fold if isinstance(fold, list) else [fold]

    return analysis


# ═══════════════════════════════════════════════════════════════
# Phase 4: 生成分析报告
# ═══════════════════════════════════════════════════════════════

def generate_report(listing: list, details: list, analyses: list):
    """生成 Markdown 分析报告"""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = OUTPUT_DIR / f"pacdora_dieline_report_{ts}.md"

    lines = [
        f"# Pacdora 刀版详情页抓取报告",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**列表页卡片数**: {len(listing)}",
        f"**详情页采样数**: {len(details)}",
        "",
        "## 1. 列表页概览",
        f"URL: {LISTING_URL}",
        f"共 {len(listing)} 个独立刀版",
        "",
    ]

    # 分类统计 (从 text 推断)
    categories = {}
    for c in listing:
        # 尝试从文本中提取分类
        t = c.get("text", "").lower()
        cat = "其他"
        for kw, label in [("box", "盒"), ("bag", "袋"), ("sleeve", "套"), ("tray", "托盘"),
                          ("mailer", "邮寄盒"), ("display", "展示"), ("tube", "管")]:
            if kw in t:
                cat = label
                break
        categories[cat] = categories.get(cat, 0) + 1
    lines.append("### 分类分布(推断)")
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        lines.append(f"- **{cat}**: {cnt}")
    lines.append("")

    # 详情页分析
    lines.append("## 2. 详情页分析")
    lines.append("")

    demo_captured = sum(1 for d in details if d.get("demo_project"))
    canvas_found = sum(1 for d in details if d.get("canvas_info"))
    svg_found = sum(1 for d in details if d.get("svg_dieline") and
                    (d["svg_dieline"].get("embedded_svgs") or d["svg_dieline"].get("svg_images")))

    lines.extend([
        f"- **demoProject JSON 拦截成功**: {demo_captured}/{len(details)}",
        f"- **3D Canvas 检测到**: {canvas_found}/{len(details)}",
        f"- **2D SVG/刀线 检测到**: {svg_found}/{len(details)}",
        "",
        "### 3D↔2D 关系分析",
        "",
    ])

    for i, (detail, analysis) in enumerate(zip(details, analyses)):
        if not detail.get("demo_project"):
            continue
        lines.append(f"#### [{detail['num']}] {detail.get('page_title', '?')[:60]}")
        lines.append(f"- URL: {detail['url']}")
        lines.append(f"- **面板数**: {len(analysis.get('panels', []))}")
        for p in analysis.get("panels", [])[:6]:
            lines.append(f"  - {p.get('name', '?')} ({p.get('width', '?')}×{p.get('height', '?')})")
        dims = analysis.get("dimensions", {})
        if dims:
            lines.append(f"- **可调尺寸**: {json.dumps(dims, ensure_ascii=False)[:200]}")
        mats = analysis.get("materials", [])
        if mats:
            lines.append(f"- **材质数**: {len(mats)}")
        geo = analysis.get("geometry_summary", {})
        if geo.get("top_keys"):
            lines.append(f"- **demoProject 顶层 key**: {geo['top_keys']}")
        canvas = detail.get("canvas_info")
        if canvas:
            for c in canvas:
                lines.append(f"- **Canvas [{c['index']}]**: {c['width']}×{c['height']}, WebGL={'✅' if c['hasWebGL'] else '❌'}")
        lines.append("")

    lines.extend([
        "## 3. 核心发现: 3D 呈现与 2D 效果的关系",
        "",
        "### 数据流",
        "```",
        "demoProject JSON",
        "  ├── pages[] → 2D 展开图面板 (每个 page = 一个可设计面)",
        "  │     ├── name: 面板名称 (正面/背面/侧面...)",
        "  │     ├── width/height: 2D 画布尺寸",
        "  │     └── elements[]: 设计元素 (文字/图片/形状)",
        "  │",
        "  ├── model/geometry → 3D 折叠模型",
        "  │     ├── vertices[]: 顶点坐标 (Three.js BufferGeometry)",
        "  │     ├── faces[]: 面索引",
        "  │     └── uv[]: UV 映射坐标 (将 2D 贴图映射到 3D 面)",
        "  │",
        "  ├── sizes → 可调尺寸参数 (长/宽/高)",
        "  │     └── 修改尺寸 → 同时更新 2D 展开图 + 3D 模型",
        "  │",
        "  └── material/modeSetting → 材质参数",
        "        ├── 纸材纹理贴图 URL",
        "        ├── 厚度/克重",
        "        └── 影响 3D 渲染材质球",
        "```",
        "",
        "### 关键映射机制",
        "1. **UV 映射**: 2D 展开图的每个面板通过 UV 坐标映射到 3D 模型的对应面",
        "2. **参数联动**: 修改 sizes 参数 → 后端重新计算 → 2D 展开图重绘 + 3D 模型顶点更新",
        "3. **面板一一对应**: pages[].name ↔ 3D model 的面(face) 是一一映射关系",
        "4. **设计实时同步**: 在 2D 画布上添加的元素(文字/图片)通过纹理贴图实时映射到 3D 预览",
        "",
    ])

    report_text = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\n📝 报告已保存: {report_path}")
    return report_path


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print("🚀 Pacdora 刀版详情页深度抓取")
    print(f"📂 输出目录: {OUTPUT_DIR}")
    print(f"🎯 列表页: {LISTING_URL}")
    print(f"📊 最大详情页采样: {MAX_DETAIL_PAGES}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100,
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            # 录制 HAR (可选, 便于后续离线分析网络请求)
            # record_har_path=str(OUTPUT_DIR / "pacdora.har"),
        )
        # 注入 WebGL 指纹保护
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = context.new_page()

        # ── Phase 1: 列表页
        listing = scrape_listing(page)

        # 保存列表数据
        listing_path = OUTPUT_DIR / "dieline_listing.json"
        with open(listing_path, "w", encoding="utf-8") as f:
            json.dump(listing, f, ensure_ascii=False, indent=2)
        print(f"💾 列表数据 → {listing_path}")

        # ── Phase 2: 详情页采样
        # 优先选择有 num 的卡片, 随机采样
        candidates = [c for c in listing if c.get("num")]
        if len(candidates) > MAX_DETAIL_PAGES:
            # 均匀采样: 头/中/尾各取一些
            step = max(1, len(candidates) // MAX_DETAIL_PAGES)
            sampled = candidates[::step][:MAX_DETAIL_PAGES]
        else:
            sampled = candidates[:MAX_DETAIL_PAGES]

        print(f"\n{'='*60}")
        print(f"Phase 2: 采样 {len(sampled)} 个详情页")
        print("=" * 60)

        details = []
        analyses = []
        for idx, card in enumerate(sampled):
            url = card["full_url"]
            num = card["num"]
            print(f"\n[{idx+1}/{len(sampled)}] num={num}")
            print(f"  URL: {url}")

            detail = scrape_detail(page, url, num)
            details.append(detail)

            # 分析 demoProject
            analysis = analyze_demo_project(detail.get("demo_project"), num)
            analyses.append(analysis)

            if detail.get("demo_project"):
                # 保存单个 demoProject JSON
                dp_path = OUTPUT_DIR / f"demoProject_{num}.json"
                with open(dp_path, "w", encoding="utf-8") as f:
                    json.dump(detail["demo_project"], f, ensure_ascii=False, indent=2)

            # 礼貌延迟
            if idx < len(sampled) - 1:
                delay = random.uniform(*REQUEST_DELAY)
                print(f"  ⏱️ 等待 {delay:.1f}s...")
                time.sleep(delay)

        # 保存全部详情数据
        details_path = OUTPUT_DIR / "dieline_details.json"
        # 去掉 demo_project 原始数据(太大), 只保留分析结果
        details_slim = []
        for d in details:
            slim = {k: v for k, v in d.items() if k != "demo_project"}
            slim["has_demo_project"] = d.get("demo_project") is not None
            details_slim.append(slim)

        with open(details_path, "w", encoding="utf-8") as f:
            json.dump(details_slim, f, ensure_ascii=False, indent=2)
        print(f"\n💾 详情数据 → {details_path}")

        analyses_path = OUTPUT_DIR / "demo_project_analyses.json"
        with open(analyses_path, "w", encoding="utf-8") as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2)
        print(f"💾 分析数据 → {analyses_path}")

        # ── Phase 3: 生成报告
        report_path = generate_report(listing, details, analyses)

        browser.close()

    print(f"\n🎉 全部完成! 输出目录: {OUTPUT_DIR}")
    print(f"   - dieline_listing.json     : 列表页卡片")
    print(f"   - dieline_details.json     : 详情页提取")
    print(f"   - demo_project_analyses.json: 3D数据分析")
    print(f"   - demoProject_*.json       : 原始3D数据")
    print(f"   - pacdora_dieline_report_*.md: 分析报告")


if __name__ == "__main__":
    main()
