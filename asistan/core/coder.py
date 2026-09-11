from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .config import AppSpec, Settings
from .hands import ActionResult


class Coder:
    """İzinli proje köklerinde dosya/site işlemleri + Cursor açma."""

    def __init__(self, settings: Settings, allowed_apps: dict[str, AppSpec]):
        self.settings = settings
        self.allowed_apps = allowed_apps
        self.workspace = Path(settings.workspace_root).expanduser()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.projects = {
            k.lower(): Path(v).expanduser() for k, v in (settings.projects or {}).items()
        }
        # Varsayılan: workspace ve tanımlı projeler
        if "asistan" not in self.projects:
            self.projects["asistan"] = Path(__file__).resolve().parent.parent
        if "workspace" not in self.projects:
            self.projects["workspace"] = self.workspace

    def resolve_project(self, name_or_path: str) -> Path | None:
        key = name_or_path.strip().lower()
        if key in self.projects:
            return self.projects[key]
        path = Path(name_or_path.strip().strip('"')).expanduser()
        if path.exists():
            return path.resolve()
        # kısmi isim
        for k, p in self.projects.items():
            if key in k or k in key:
                return p
        return None

    def allowed_roots(self) -> list[Path]:
        roots = [self.workspace.resolve()]
        for p in self.projects.values():
            try:
                roots.append(p.resolve())
            except Exception:
                continue
        return roots

    def _ensure_inside(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        for root in self.allowed_roots():
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        raise PermissionError(f"İzinli proje kökü dışında: {resolved}")

    def open_in_cursor(self, project: str | None = None, monitor: int | None = None) -> ActionResult:
        target: Path | None
        if project:
            target = self.resolve_project(project)
            if target is None:
                return ActionResult(False, f"Proje bulunamadı: {project}")
        else:
            target = self.workspace

        cursor = self.allowed_apps.get("cursor")
        exe = cursor.path if cursor else self.settings.cursor_cli
        try:
            subprocess.Popen([exe, str(target)], shell=False)
        except FileNotFoundError:
            # Windows yaygın yollar
            candidates = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor" / "Cursor.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Cursor" / "Cursor.exe",
            ]
            launched = False
            for cand in candidates:
                if cand.exists():
                    subprocess.Popen([str(cand), str(target)], shell=False)
                    launched = True
                    break
            if not launched:
                return ActionResult(
                    False,
                    "Cursor bulunamadı. PATH'e `cursor` ekle veya config'de cursor path yaz.",
                )
        msg = f"Cursor'da açıldı: {target}"
        data: dict[str, Any] = {"path": str(target)}
        if monitor is not None:
            data["monitor"] = monitor
            msg += f" (ekran {monitor} için taşıma ayrı open_app ile yapılabilir)"
        return ActionResult(True, msg, data=data)

    def create_site(self, brief: str, open_cursor: bool = True) -> ActionResult:
        slug = _slugify(brief) or "yeni-site"
        site_dir = self._ensure_inside(self.workspace / "sites" / slug)
        site_dir.mkdir(parents=True, exist_ok=True)
        title = brief.strip().capitalize()[:80] or "Yeni Site"
        (site_dir / "index.html").write_text(_site_html(title, brief), encoding="utf-8")
        (site_dir / "styles.css").write_text(_site_css(), encoding="utf-8")
        (site_dir / "app.js").write_text(_site_js(), encoding="utf-8")
        (site_dir / "README.md").write_text(
            f"# {title}\n\nİstek: {brief}\n\nVanilla HTML/CSS/JS. `index.html` ile aç.\n",
            encoding="utf-8",
        )
        data = {"path": str(site_dir)}
        if open_cursor:
            opened = self.open_in_cursor(str(site_dir))
            data["cursor"] = opened.message
            if not opened.ok:
                return ActionResult(
                    True,
                    f"Site oluşturuldu: {site_dir}. Cursor açılamadı: {opened.message}",
                    data=data,
                )
        return ActionResult(True, f"Site hazır ve Cursor'da açıldı: {site_dir}", data=data)

    def write_file(self, relative: str, content: str, project: str = "workspace") -> ActionResult:
        root = self.resolve_project(project) or self.workspace
        path = self._ensure_inside(root / relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ActionResult(True, f"Yazıldı: {path}", data={"path": str(path)})

    def append_file(self, relative: str, content: str, project: str = "workspace") -> ActionResult:
        root = self.resolve_project(project) or self.workspace
        path = self._ensure_inside(root / relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return ActionResult(True, f"Eklendi: {path}", data={"path": str(path)})

    def write_agent_prompt(self, prompt: str, project: str | None = None) -> ActionResult:
        """Cursor Agent için görev notu bırakır ve projeyi açar."""
        root = self.resolve_project(project or "workspace") or self.workspace
        path = self._ensure_inside(root / "JARVIS_GOREV.md")
        path.write_text(
            "# Jarvis görev notu\n\n"
            "Bu dosyayı Cursor Agent / Chat'e vererek devam ettirebilirsin.\n\n"
            f"## İstek\n\n{prompt.strip()}\n",
            encoding="utf-8",
        )
        opened = self.open_in_cursor(str(root))
        return ActionResult(
            True,
            f"Görev notu yazıldı ({path.name}). Cursor açıldı. Agent'a bu dosyayı gösterebilirsin.",
            data={"path": str(path), "cursor_ok": opened.ok},
        )

    def list_projects(self) -> ActionResult:
        data = {k: str(v) for k, v in sorted(self.projects.items())}
        return ActionResult(True, "Kayıtlı projeler", data={"projects": data})


def _slugify(text: str) -> str:
    text = text.lower().strip()
    repl = str.maketrans("çğıöşü", "cgiosu")
    text = text.translate(repl)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:48]


def _site_html(title: str, brief: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div class="bg" aria-hidden="true"></div>
  <header class="hero">
    <p class="brand">{_esc(title)}</p>
    <h1>Hoş geldin</h1>
    <p class="lead">{_esc(brief)}</p>
    <div class="cta">
      <a class="btn" href="#icerik">Keşfet</a>
    </div>
  </header>
  <main id="icerik" class="section">
    <h2>Hakkında</h2>
    <p>Bu iskelet Jarvis tarafından oluşturuldu. Cursor'da düzenleyebilirsin.</p>
  </main>
  <script src="app.js"></script>
</body>
</html>
"""


def _site_css() -> str:
    return """:root {
  --bg: #12100e;
  --ink: #f3ebe1;
  --muted: #b7a899;
  --accent: #c45c26;
  --font-display: "Fraunces", serif;
  --font-body: "Manrope", sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; font-family: var(--font-body); color: var(--ink); background: var(--bg); }
.bg {
  position: fixed; inset: 0; z-index: -1;
  background:
    radial-gradient(ellipse 70% 50% at 20% 10%, rgba(196,92,38,.25), transparent 55%),
    linear-gradient(160deg, #12100e, #1c1814 60%, #0e0c0a);
}
.hero {
  min-height: 100vh; display: flex; flex-direction: column; justify-content: flex-end;
  padding: clamp(1.5rem, 5vw, 4rem); padding-bottom: 18vh;
  animation: rise .8s ease both;
}
.brand {
  margin: 0 0 .6rem; font-family: var(--font-display);
  font-size: clamp(2.4rem, 8vw, 4.5rem); letter-spacing: -.02em;
}
.hero h1 { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.lead { max-width: 32rem; color: var(--muted); font-size: 1.1rem; line-height: 1.55; }
.cta { margin-top: 1.4rem; }
.btn {
  display: inline-block; padding: .85rem 1.3rem; background: var(--accent); color: #fff;
  text-decoration: none; font-weight: 600; transition: transform .15s ease;
}
.btn:hover { transform: translateY(-1px); }
.section { padding: clamp(2rem, 6vw, 5rem); max-width: 40rem; animation: rise .9s .1s ease both; }
@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
"""


def _site_js() -> str:
    return """document.querySelectorAll('a[href^=\"#\"]').forEach((a) => {
  a.addEventListener('click', (e) => {
    const id = a.getAttribute('href');
    const el = id && document.querySelector(id);
    if (!el) return;
    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth' });
  });
});
"""


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
