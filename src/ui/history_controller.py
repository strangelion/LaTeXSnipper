"""History controller mixin for the main window."""

from __future__ import annotations

import pyperclip
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import Action, InfoBar, InfoBarPosition

from runtime.config_manager import normalize_content_type
from runtime.history_store import load_history_store, save_history_store
from sharing.history_package import build_history_package, merge_history_package
from sharing.lan_share_server import LanShareServer
from ui.edit_formula_dialog import EditFormulaDialog
from ui.formula_export_menu import populate_formula_export_menu
from ui.history_panel import (
    clear_history_rows,
    create_history_row as create_history_row_widget,
    history_display_entries,
    refresh_history_order_button,
)
from ui.menu_helpers import CenterMenu
from ui.window_helpers import (
    apply_no_minimize_window_flags,
    exec_close_only_message_box as _exec_close_only_message_box,
    show_formula_rename_dialog as _show_formula_rename_dialog,
)

try:
    from PyQt6 import sip
except Exception:
    try:
        import sip  # pyright: ignore[reportMissingImports]
    except Exception:
        sip = None

MAX_HISTORY = 200


class HistoryControllerMixin:
    def _build_share_history_package(self):
        return build_history_package(
            self.history,
            self._formula_names,
            self._formula_types,
            getattr(self, "_history_render_tags", None),
            source="desktop",
        )

    def _import_share_history_package(self, package):
        added, updated = merge_history_package(
            package,
            self.history,
            self._formula_names,
            self._formula_types,
            self._history_render_tags,
            max_history=MAX_HISTORY,
        )
        self.save_history()
        QTimer.singleShot(0, self.rebuild_history_ui)
        QTimer.singleShot(0, lambda: self.set_action_status(f"共享导入完成：新增 {added} 条"))
        return added, updated

    def show_lan_share_dialog(self):
        """Open LAN and encrypted WebDAV sharing tools."""
        from preview.math_preview import dialog_theme_tokens, is_dark_ui
        from PyQt6.QtCore import QThread, pyqtSignal
        from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout
        from qfluentwidgets import PrimaryPushButton

        server = getattr(self, "_lan_share_server", None)
        if server is not None:
            try:
                server.stop()
            except Exception:
                pass
            self._lan_share_server = None

        t = dialog_theme_tokens()
        dark = is_dark_ui()
        selection_bg = "#3b4756" if dark else "#d7e3f1"
        focus_border = "#66788a" if dark else "#9aa9bb"

        input_qss = f"""
            QLineEdit {{
                background: {t['panel_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 5px 8px;
                selection-background-color: {selection_bg};
                selection-color: {t['text']};
            }}
            QLineEdit:focus {{
                border: 1px solid {focus_border};
            }}
            QLineEdit:disabled {{
                background: {t['panel_bg']};
                color: {t['muted']};
            }}
        """
        label_qss = f"color: {t['text']}; font-weight: 500;"
        hint_qss = f"color: {t['muted']}; font-size: 11px;"
        section_title_qss = f"color: {t['accent']}; font-weight: 600; font-size: 13px; margin-top: 8px;"

        dlg = QDialog(self)
        dlg.setWindowTitle("共享")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(f"QDialog {{ background: {t['window_bg']}; }}")
        apply_no_minimize_window_flags(dlg)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        lan_title = QLabel("局域网共享")
        lan_title.setStyleSheet(section_title_qss)
        layout.addWidget(lan_title)

        lan_hint = QLabel("正在启动共享服务…")
        lan_hint.setStyleSheet(f"color: {t['muted']}; font-size: 12px; line-height: 1.5;")
        lan_hint.setWordWrap(True)
        layout.addWidget(lan_hint)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {t['border']};")
        layout.addWidget(sep)

        webdav_title = QLabel("WebDAV 加密同步")
        webdav_title.setStyleSheet(section_title_qss)
        layout.addWidget(webdav_title)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setSpacing(8)

        webdav_url = QLineEdit()
        webdav_url.setPlaceholderText("https://dav.example.com/user/  (自动存储到 latexsnipper/ 子目录)")
        webdav_url.setStyleSheet(input_qss)
        webdav_url.setFixedHeight(32)

        webdav_user = QLineEdit()
        webdav_user.setPlaceholderText("用户名")
        webdav_user.setStyleSheet(input_qss)
        webdav_user.setFixedHeight(32)

        webdav_password = QLineEdit()
        webdav_password.setEchoMode(QLineEdit.EchoMode.Password)
        webdav_password.setPlaceholderText("WebDAV 密码")
        webdav_password.setStyleSheet(input_qss)
        webdav_password.setFixedHeight(32)

        encrypt_password = QLineEdit()
        encrypt_password.setEchoMode(QLineEdit.EchoMode.Password)
        encrypt_password.setPlaceholderText("至少 8 位，用于 AES-GCM 加密")
        encrypt_password.setStyleSheet(input_qss)
        encrypt_password.setFixedHeight(32)

        for label_text, widget in [
            ("文件 URL", webdav_url),
            ("用户名", webdav_user),
            ("WebDAV 密码", webdav_password),
            ("加密密码", encrypt_password),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(label_qss)
            form.addRow(lbl, widget)

        layout.addLayout(form)

        from sharing.webdav_sync import has_saved_webdav_credentials, load_webdav_credentials

        saved_hint = has_saved_webdav_credentials()
        status = QLabel(
            "凭据已加密保存（无法查看，填写新值可覆盖）。文件将存储到 latexsnipper/ 子目录。" if saved_hint
            else "首次填写后将加密保存到本地，之后无法查看，只能覆盖。文件将存储到 latexsnipper/ 子目录。"
        )
        status.setStyleSheet(hint_qss)
        layout.addWidget(status)

        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background: {t['border']};")
        layout.addWidget(sep2)

        auto_sync_title = QLabel("定时同步")
        auto_sync_title.setStyleSheet(section_title_qss)
        layout.addWidget(auto_sync_title)

        auto_sync_row = QHBoxLayout()
        auto_sync_row.setSpacing(8)
        auto_sync_check = QCheckBox("启用定时同步")
        auto_sync_check.setStyleSheet(f"color: {t['text']}; font-size: 12px;")
        auto_sync_interval = QComboBox()
        auto_sync_interval.addItems(["5 分钟", "15 分钟", "30 分钟", "1 小时", "2 小时"])
        auto_sync_interval.setCurrentIndex(1)
        auto_sync_interval.setStyleSheet(input_qss)
        auto_sync_interval.setFixedHeight(28)
        auto_sync_interval.setFixedWidth(100)
        auto_sync_row.addWidget(auto_sync_check)
        auto_sync_row.addWidget(QLabel("间隔:"))
        auto_sync_row.addWidget(auto_sync_interval)
        auto_sync_row.addStretch()
        layout.addLayout(auto_sync_row)

        auto_sync_hint = QLabel("启用后，桌面端会定时从 WebDAV 拉取并合并最新历史。需先填写上方 WebDAV 凭据。")
        auto_sync_hint.setStyleSheet(hint_qss)
        auto_sync_hint.setWordWrap(True)
        layout.addWidget(auto_sync_hint)

        sync_status_label = QLabel("")
        sync_status_label.setStyleSheet(hint_qss)
        layout.addWidget(sync_status_label)

        INTERVAL_MS = [300_000, 900_000, 1_800_000, 3_600_000, 7_200_000]
        auto_sync_timer = QTimer(self)
        auto_sync_timer.setSingleShot(True)

        def do_auto_sync():
            if not auto_sync_check.isChecked():
                return
            url_val, user_val, pwd_val, enc_val = webdav_settings()
            if not url_val or not enc_val:
                sync_status_label.setText("跳过同步：未填写 WebDAV 凭据")
                auto_sync_timer.start(INTERVAL_MS[auto_sync_interval.currentIndex()])
                return

            def _do():
                from sharing.webdav_sync import download_package
                pkg = download_package(url_val, user_val, pwd_val, enc_val)
                added, updated = self._import_share_history_package(pkg)
                return added, updated

            class SyncWorker(QThread):
                finished = pyqtSignal(object)
                error = pyqtSignal(str)

                def __init__(self, fn):
                    super().__init__()
                    self._fn = fn

                def run(self):
                    try:
                        result = self._fn()
                        self.finished.emit(result)
                    except Exception as exc:
                        self.error.emit(str(exc))

            def on_sync_done(result):
                if isinstance(result, tuple):
                    added, updated = result
                    sync_status_label.setText(
                        f"上次同步: 新增 {added} 条，更新 {updated} 条"
                    )
                auto_sync_timer.start(INTERVAL_MS[auto_sync_interval.currentIndex()])

            def on_sync_error(msg):
                sync_status_label.setText(f"同步失败: {msg}")
                auto_sync_timer.start(INTERVAL_MS[auto_sync_interval.currentIndex()])

            sync_status_label.setText("正在同步…")
            w = SyncWorker(_do)
            w.finished.connect(on_sync_done)
            w.error.connect(on_sync_error)
            w.start()

        def toggle_auto_sync(state):
            auto_sync_timer.stop()
            if state:
                do_auto_sync()
            else:
                sync_status_label.setText("")

        auto_sync_check.stateChanged.connect(toggle_auto_sync)

        set_busy = [False]

        class WebdavWorker(QThread):
            finished = pyqtSignal(str)

            def __init__(self, fn):
                super().__init__()
                self._fn = fn

            def run(self):
                try:
                    self._fn()
                except Exception as exc:
                    self.finished.emit(str(exc))

        def webdav_settings():
            return (
                webdav_url.text().strip(),
                webdav_user.text().strip(),
                webdav_password.text(),
                encrypt_password.text(),
            )

        worker_ref = [None]

        def set_buttons_busy(busy):
            set_busy[0] = busy
            for btn in (upload_btn, download_btn):
                btn.setEnabled(not busy)
            status.setText("正在处理…" if busy else "")

        def on_worker_done(msg):
            set_buttons_busy(False)
            status.setStyleSheet(f"color: {t['text']}; font-size: 11px;")
            status.setText(msg)

        def upload_webdav():
            if set_busy[0]:
                return
            set_buttons_busy(True)
            status.setStyleSheet(f"color: {t['muted']}; font-size: 11px;")

            def _do():
                from sharing.webdav_sync import upload_package, save_webdav_credentials
                url_val, user_val, pwd_val, enc_val = webdav_settings()
                pkg = self._build_share_history_package()
                upload_package(url_val, user_val, pwd_val, enc_val, pkg)
                save_webdav_credentials(url_val, user_val, pwd_val, enc_val)

            w = WebdavWorker(_do)
            w.finished.connect(on_worker_done)
            worker_ref[0] = w
            w.start()

        def download_webdav():
            if set_busy[0]:
                return
            set_buttons_busy(True)
            status.setStyleSheet(f"color: {t['muted']}; font-size: 11px;")

            def _do():
                from sharing.webdav_sync import download_package, save_webdav_credentials
                url_val, user_val, pwd_val, enc_val = webdav_settings()
                pkg = download_package(url_val, user_val, pwd_val, enc_val)
                added, updated = self._import_share_history_package(pkg)
                save_webdav_credentials(url_val, user_val, pwd_val, enc_val)
                on_worker_done(f"已合并：新增 {added} 条，更新 {updated} 条")

            w = WebdavWorker(_do)
            w.finished.connect(lambda msg: on_worker_done(msg))
            worker_ref[0] = w
            w.start()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        download_btn = PrimaryPushButton("下载并合并")
        download_btn.setFixedHeight(32)
        upload_btn = PrimaryPushButton("加密上传")
        upload_btn.setFixedHeight(32)
        close_btn = PrimaryPushButton("关闭")
        close_btn.setFixedHeight(32)
        btn_row.addWidget(download_btn)
        btn_row.addWidget(upload_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        upload_btn.clicked.connect(upload_webdav)
        download_btn.clicked.connect(download_webdav)
        close_btn.clicked.connect(dlg.accept)

        def _start_lan_server():
            def _recognize_image(image_bytes: bytes, mode: str) -> dict:
                from io import BytesIO
                from PIL import Image
                img = Image.open(BytesIO(image_bytes))
                model = getattr(self, "model", None)
                if model is None:
                    raise RuntimeError("OCR model not loaded")
                result = model.predict_result(img, model_name="mathcraft")
                return {
                    "latex": str(result.get("text", "") or "").strip(),
                    "score": result.get("score"),
                    "mode": result.get("mode", mode),
                }

            try:
                srv = LanShareServer(
                    self._build_share_history_package,
                    self._import_share_history_package,
                    recognize_provider=_recognize_image,
                )
                srv.start()
                self._lan_share_server = srv
                urls = "\n".join(srv.display_urls())
                lan_hint.setText(
                    f"手机端打开 历史 → 共享，填写任一地址和 PIN\n"
                    f"地址: {urls}\n"
                    f"PIN: {srv.pin}"
                )
                lan_hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                lan_hint.setStyleSheet(f"color: {t['text']}; font-size: 12px; line-height: 1.5;")
            except Exception as exc:
                lan_hint.setText(f"启动失败: {exc}")
                lan_hint.setStyleSheet(f"color: #d32f2f; font-size: 12px;")

        def _load_saved_credentials():
            creds = load_webdav_credentials()
            if creds:
                webdav_url.setText(creds.get("url", ""))
                webdav_user.setText(creds.get("username", ""))
                webdav_password.setText(creds.get("password", ""))
                encrypt_password.setText(creds.get("encrypt_password", ""))

        QTimer.singleShot(0, _start_lan_server)
        QTimer.singleShot(50, _load_saved_credentials)

        try:
            dlg.exec()
        finally:
            auto_sync_timer.stop()
            if worker_ref[0] is not None and worker_ref[0].isRunning():
                worker_ref[0].quit()
                worker_ref[0].wait(2000)
            try:
                server_obj = getattr(self, "_lan_share_server", None)
                if server_obj is not None:
                    server_obj.stop()
            except Exception:
                pass
            self._lan_share_server = None
    def _show_history_context_menu(self, row: QWidget, global_pos):
        if not self._row_is_alive(row):
            return
        latex = self._safe_row_text(row)
        m = CenterMenu(parent=self)
        m.addAction(Action("编辑", triggered=lambda: self._edit_history_row(row)))
        m.addAction(Action("复制", triggered=lambda: self._do_copy_row(row)))
        m.addAction(Action("收藏", triggered=lambda: self._do_fav_row(row)))

        export_menu = CenterMenu("导出为...", parent=m)
        populate_formula_export_menu(export_menu, lambda format_type: self._export_as(format_type, latex))
        m.addMenu(export_menu)

        m.addAction(Action("重命名", triggered=lambda: self._rename_history_row(row)))
        m.addAction(Action("删除", triggered=lambda: self._do_delete_row(row)))
        m.exec(global_pos)

    def _rename_history_row(self, row: QWidget):
        """Rename a formula history row."""
        latex = self._safe_row_text(row)
        if not latex:
            return
        current_name = self._formula_names.get(latex, "")
        new_name, ok = _show_formula_rename_dialog(
            self,
            current_name=current_name,
            title="重命名公式",
            prompt="输入公式名称（留空则清除名称）：",
        )
        if not ok:
            return
        if new_name:
            self._formula_names[latex] = new_name
            if hasattr(self, "favorites_window") and self.favorites_window:
                self.favorites_window._favorite_names[latex] = new_name
                self.favorites_window.save_favorites()
                self.favorites_window.refresh_list()
        else:
            self._formula_names.pop(latex, None)
            if (
                hasattr(self, "favorites_window")
                and self.favorites_window
            ):
                self.favorites_window._favorite_names.pop(latex, None)
                self.favorites_window.save_favorites()
                self.favorites_window.refresh_list()
        self.save_history()



        for i, (formula, label) in enumerate(self._rendered_formulas):
            if formula == latex:
                s = (label or "").strip()
                prefix = ""
                if s.startswith("#"):
                    prefix = s.split(" ", 1)[0]
                if new_name:
                    new_label = f"{prefix} {new_name}".strip() if prefix else new_name
                else:
                    new_label = prefix
                self._rendered_formulas[i] = (formula, new_label)


        self.rebuild_history_ui()
        self._refresh_preview()
        self.set_action_status(f"已命名: {new_name}" if new_name else "已清除名称")

    def _history_row_index(self, row: QWidget):
        actual_index = getattr(row, "_history_index", None)
        if isinstance(actual_index, int) and 0 <= actual_index < len(self.history):
            return actual_index

        total = self.history_layout.count() - 1
        for i in range(total):
            item = self.history_layout.itemAt(i)
            w = item.widget() if item else None
            if w is row:
                return i
        return None

    def _edit_history_row(self, row: QWidget):
        old_latex = getattr(row, "_latex_text", "")
        dlg = EditFormulaDialog(old_latex, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_latex = dlg.value()
        if not new_latex or new_latex == old_latex:
            return


        if old_latex in self._formula_names:
            self._formula_names[new_latex] = self._formula_names.pop(old_latex)
        if old_latex in self._formula_types:
            self._formula_types[new_latex] = self._formula_types.pop(old_latex)


        row._latex_text = new_latex
        lbl = getattr(row, "_content_label", None)
        if lbl:
            lbl.setText(new_latex)
            self._apply_formula_label_theme(lbl)

        idx = self._history_row_index(row)
        if idx is not None and 0 <= idx < len(self.history):
            self.history[idx] = new_latex
            try:
                self.save_history()
            except Exception as e:
                print("[WARN] 保存历史失败:", e)


        for i, (formula, label) in enumerate(self._rendered_formulas):
            if formula == old_latex:
                self._rendered_formulas[i] = (new_latex, label)
        self._refresh_preview()

        self.set_action_status("已更新")

    def _history_display_entries(self):
        return history_display_entries(self.history, bool(getattr(self, "history_reverse", False)))

    def _refresh_history_order_button(self):
        refresh_history_order_button(
            getattr(self, "history_order_button", None),
            bool(getattr(self, "history_reverse", False)),
        )

    def toggle_history_order(self):
        self.history_reverse = not bool(getattr(self, "history_reverse", False))
        self.cfg.set("history_reverse", self.history_reverse)
        self._refresh_history_order_button()
        self.rebuild_history_ui()

    def rebuild_history_ui(self):
        clear_history_rows(self.history_layout)
        for display_index, history_index, text in self._history_display_entries():
            self.history_layout.insertWidget(
                self.history_layout.count() - 1,
                self.create_history_row(text, display_index, history_index),
            )
        self._refresh_history_order_button()
        self.update_history_ui()

    def _row_is_alive(self, row):
        if not row:
            return False
        if getattr(row, "_deleted", False):
            return False
        if sip and hasattr(sip, "isdeleted"):
            if sip.isdeleted(row):
                return False

        if row.parent() is None:
            return False
        return True

    def _safe_row_text(self, row):
        if not self._row_is_alive(row):
            return ""
        return (getattr(row, "_latex_text", "") or "").strip()

    def _do_copy_row(self, row):
        txt = self._safe_row_text(row)
        if not txt:
            self.set_action_status("内容不存在")
            return
        try:
            QApplication.clipboard().setText(txt)
            self.set_action_status("已复制")
        except Exception:
            try:
                pyperclip.copy(txt)
                self.set_action_status("已复制")
            except Exception:
                self.set_action_status("复制失败")

    def _do_fav_row(self, row):
        txt = self._safe_row_text(row)
        if not txt:
            self.set_action_status("内容不存在")
            return
        content_type = None
        try:
            if hasattr(self, "_formula_types"):
                content_type = self._formula_types.get(txt)
        except Exception:
            content_type = None
        if not content_type:
            try:
                content_type = getattr(getattr(self, "model", None), "last_used_model", None)
            except Exception:
                content_type = None
        if not content_type:
            content_type = getattr(self, "current_model", "mathcraft")
        self._ensure_favorites_window().add_favorite(txt, content_type=content_type)

    def _do_delete_row(self, row):
        txt = self._safe_row_text(row)
        if not txt:
            self.set_action_status("已删除（空）")
            return

        self.delete_history_item(row, txt)

    def _load_history_row_to_editor(self, row):
        txt = self._safe_row_text(row)
        if txt:
            # In Typst mode, convert LaTeX-stored content to Typst on load
            # and always wrap in $$...$$ for display-math rendering.
            text_to_set = txt
            try:
                from exporting.formula_converters import get_current_render_mode
                from core.mathcraft_document_engine import convert_latex_to_typst
                stored_tag = self._history_render_tags.get(txt, "")
                if get_current_render_mode() == "typst":
                    if stored_tag != "typst":
                        text_to_set = convert_latex_to_typst(txt)
                    # Always wrap Typst content in $$ for the main editor
                    if text_to_set and not text_to_set.startswith("$"):
                        text_to_set = "$$ " + text_to_set + " $$"
            except Exception:
                pass
            self._set_editor_text_silent(text_to_set)
            idx = getattr(row, '_index', 0)
            name = self._formula_names.get(txt, "")
            if name:
                label = f"#{idx} {name}"
            elif idx > 0:
                label = f"#{idx}"
            else:
                label = ""
            self.render_latex_in_preview(text_to_set, label)
            self.set_action_status("已加载到编辑器")

    def create_history_row(self, t: str, index: int = 0, history_index: int | None = None):
        return create_history_row_widget(
            parent=self,
            history_container=self.history_container,
            text=t,
            index=index,
            history_index=history_index,
            formula_names=self._formula_names,
            render_tags=getattr(self, "_history_render_tags", None),
            apply_row_theme=self._apply_history_row_theme,
            row_is_alive=self._row_is_alive,
            on_load_to_editor=self._load_history_row_to_editor,
            on_copy=self._do_copy_row,
            on_context_menu=self._show_history_context_menu,
        )

    def add_history_record(self, text: str, content_type: str = None, *, render_tag: str = ""):
        t = (text or "").strip()
        if not t:
            return

        if content_type is None:
            content_type = getattr(self, "current_model", "mathcraft")
        self._formula_types[t] = normalize_content_type(content_type)

        # Record which render engine format this was stored as
        tag = str(render_tag or "").strip().lower()
        if tag in ("latex", "typst"):
            if not hasattr(self, "_history_render_tags"):
                self._history_render_tags = {}
            self._history_render_tags[t] = tag
        elif hasattr(self, "_history_render_tags") and t in self._history_render_tags:
            # Keep existing tag if no new tag specified
            pass

        self.history.append(t)

        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
        self.save_history()
        self.rebuild_history_ui()
        self.set_action_status("已加入历史")
        print(f"[HistoryAdd] total={len(self.history)} type={content_type} last='{t[:60]}'")

    def load_history(self):
        try:
            self.history, self._formula_names, self._formula_types, self._history_render_tags = load_history_store(self.history_path)
        except Exception as e:
            print("加载历史失败:", e)
            self.history = []
            self._history_render_tags = {}
        self.rebuild_history_ui()

    def delete_history_item(self, widget, text):
        print(f"[Delete] request text='{text}' history_len={len(self.history)}")
        if text in self.history:
            self.history.remove(text)
        if widget:

            try:
                if self.history_layout.indexOf(widget) != -1:
                    self.history_layout.removeWidget(widget)
            except Exception:
                pass
            widget.setParent(None)
            widget.deleteLater()
        self.save_history()
        self.set_action_status("已删除")
        self.update_history_ui()

    def update_history_ui(self):
        self.clear_history_button.setText("清空历史记录")
        if self.history:

            self.clear_history_button.setToolTip("清空所有历史记录")
        else:

            self.clear_history_button.setToolTip("当前无历史记录，点击会提示")

        self.clear_history_button.setEnabled(True)

    def save_history(self):
        try:
            save_history_store(
                self.history_path,
                self.history,
                self._formula_names,
                self._formula_types,
                getattr(self, "_history_render_tags", None),
            )
        except Exception as e:
            print("历史保存失败:", e)

    def clear_history(self):

        if not self.history:
            InfoBar.info(
                title="提示",
                content="当前没有历史记录可清空",
                parent=self._get_infobar_parent(),
                duration=2500,
                position=InfoBarPosition.TOP,
            )
            return
        ret = _exec_close_only_message_box(
            self,
            "确认",
            f"确定要清空所有 {len(self.history)} 条历史记录吗？",
            icon=QMessageBox.Icon.Question,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.history.clear()
        self.save_history()
        self.rebuild_history_ui()
        self.update_history_ui()
        self.set_action_status("已清空历史")
