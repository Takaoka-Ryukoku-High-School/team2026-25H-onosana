import base64
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import flet as ft


DATA_FILE = Path.home() / ".controller_wiring_registry.json"


def diagnose_wiring(
    voltage: float,
    ground_ok: bool,
    signal_state: str | list[str],
    connector_state: str | list[str],
    heat_state: str | list[str],
    noise_state: str,
    cable_length: str,
) -> tuple[int, str, list[str], list[str]]:
    score = 100
    issues: list[str] = []
    actions: list[str] = []

    if voltage < 11.0 or voltage > 13.8:
        score -= 30
        issues.append("電源電圧が仕様範囲外です。")
        actions.append("電源供給と負荷の確認を行い、電圧計で再測定してください。")
    elif voltage < 12.0:
        score -= 12
        issues.append("電源がやや不足気味です。")
        actions.append("電源ラインの接触不良や配線抵抗を確認してください。")

    if not ground_ok:
        score -= 35
        issues.append("グランド接続が不良です。")
        actions.append("アース線の接続箇所と端子の緩みを確認し、接地抵抗を測定してください。")

    if "断線" in signal_state:
        score -= 35
        issues.append("信号線に断線の可能性があります。")
        actions.append("各信号ラインを途中でチェックし、コネクタと端子を点検してください。")
    if "短絡" in signal_state:
        score -= 40
        issues.append("信号線が短絡している可能性があります。")
        actions.append("短絡箇所を特定し、絶縁や配線ルートを見直してください。")
    if "ノイズあり" in signal_state:
        score -= 20
        issues.append("ノイズが混入している可能性があります。")
        actions.append("配線の束ね方を見直し、ハーネスの分離とシールド対策を検討してください。")

    if "ゆるい" in connector_state:
        score -= 18
        issues.append("コネクタが緩んでいます。")
        actions.append("コネクタの固定、端子の圧着、ロック機構を確認してください。")
    if "接触不良" in connector_state:
        score -= 20
        issues.append("配線または端子に接触不良の可能性があります。")
        actions.append("配線と端子の接続状態を確認し、接点の清掃や端子の締め直しを行ってください。")
    if "腐食" in connector_state:
        score -= 25
        issues.append("コネクタの腐食が見られます。")
        actions.append("接点の清掃または交換を行い、保護カバーの設置を検討してください。")

    if "高い" in heat_state:
        score -= 25
        issues.append("配線または端子の発熱が大きいです。")
        actions.append("負荷状況と接触抵抗を確認し、過負荷や断線がないかを検査してください。")
    elif "やや高い" in heat_state:
        score -= 10
        issues.append("発熱が少し見られます。")
        actions.append("温度上昇箇所を監視し、今後の負荷増加に備えて点検を行ってください。")

    if noise_state == "発生":
        score -= 15
        issues.append("誤動作やノイズが発生しています。")
        actions.append("制御線と電源線の分離、接地の見直し、フィルターの追加を検討してください。")

    if cable_length == "長い":
        score -= 10
        issues.append("配線長が長く、電圧降下やノイズの影響が出やすい状態です。")
        actions.append("ハーネスの長さを短くするか、太さのあるケーブルへの変更を検討してください。")

    if not issues:
        status = "正常"
    elif score >= 75:
        status = "要注意"
    elif score >= 50:
        status = "要点検"
    else:
        status = "重大不良"

    if not actions:
        actions = ["異常は見当たりません。通常どおりの保守で問題ありません。"]

    score = max(0, min(score, 100))
    return score, status, issues, actions


def load_registry() -> dict:
    if not DATA_FILE.exists():
        return {"controllers": []}
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"controllers": []}

    if not isinstance(data, dict):
        return {"controllers": []}

    controllers = data.get("controllers", [])
    if not isinstance(controllers, list):
        return {"controllers": []}

    cleaned = []
    for controller in controllers:
        if not isinstance(controller, dict):
            continue
        if not isinstance(controller.get("id"), str):
            continue
        if not isinstance(controller.get("name"), str):
            continue
        history = controller.get("history", [])
        if not isinstance(history, list):
            history = []
        cleaned.append(
            {
                "id": controller["id"],
                "name": controller["name"],
                "model": controller.get("model", ""),
                "location": controller.get("location", ""),
                "note": controller.get("note", ""),
                "photo_data": (
                    controller["photo_data"]
                    if isinstance(controller.get("photo_data"), str)
                    and controller["photo_data"].startswith("data:image/")
                    else None
                ),
                "created_at": controller.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "history": history,
            }
        )
    return {"controllers": cleaned}


def save_registry(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def status_color(status: str) -> str:
    palette = {
        "正常": "#2E6654",
        "要注意": "#C98A2A",
        "要点検": "#C86342",
        "重大不良": "#A43A2F",
    }
    return palette.get(status, "#64706A")


def main(page: ft.Page):
    page.title = "コントローラ登録 & 配線状態管理"
    page.bgcolor = "#F5F4EE"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    photo_picker = ft.FilePicker()
    page.services.append(photo_picker)
    photo_data: str | None = None

    controller_name = ft.TextField(label="制御器名（必須）", width=240)
    controller_model = ft.TextField(label="機種名 / 型番（任意）", width=240)
    controller_location = ft.TextField(label="設置場所（任意）", width=240)
    controller_note = ft.TextField(label="備考（任意）", multiline=True, min_lines=3, max_lines=5, width=500)
    photo_preview = ft.Image(
        src="",
        width=260,
        height=180,
        fit=ft.BoxFit.CONTAIN,
        border_radius=8,
        visible=False,
    )
    photo_status = ft.Text("写真は選択されていません。", size=12, color="#59635D")
    photo_error = ft.Text("", size=12, color="#B24A36")
    editing_controller_id: str | None = None
    register_button = ft.Button(
        "登録して状態を記録",
        icon=ft.Icons.SAVE_ALT_ROUNDED,
    )
    save_changes_button = ft.Button("変更を保存", visible=False, icon=ft.Icons.SAVE_OUTLINED)
    cancel_edit_button = ft.TextButton("編集をキャンセル", visible=False)

    voltage_field = ft.TextField(label="電源電圧（V）", value="12.0", width=220)
    ground_fault_checkbox = ft.Checkbox(label="グランド接続不良")
    signal_break_checkbox = ft.Checkbox(label="断線")
    signal_short_checkbox = ft.Checkbox(label="短絡")
    signal_noise_checkbox = ft.Checkbox(label="信号線ノイズ")
    connector_loose_checkbox = ft.Checkbox(label="コネクタのゆるみ")
    contact_failure_checkbox = ft.Checkbox(label="接触不良")
    connector_corrosion_checkbox = ft.Checkbox(label="コネクタの腐食")
    heat_moderate_checkbox = ft.Checkbox(label="発熱がやや高い")
    heat_high_checkbox = ft.Checkbox(label="発熱が高い")
    noise_checkbox = ft.Checkbox(label="誤動作・ノイズが発生")
    cable_long_checkbox = ft.Checkbox(label="配線が長い")

    summary_text = ft.Text("総合診断: まだ診断していません", size=20, weight=ft.FontWeight.BOLD)
    score_text = ft.Text("診断スコア: 0 / 100", size=16, color="#2F3B2F")
    issue_list = ft.Column()
    advice_text = ft.Text("診断結果がここに表示されます。", size=14, color="#4E584D")

    detail_title = ft.Text("コントローラ詳細", size=22, weight=ft.FontWeight.BOLD)
    detail_meta = ft.Text("最新の状態記録を選んでください。", size=13, color="#59635D")
    detail_photo = ft.Image(
        src="",
        width=320,
        height=220,
        fit=ft.BoxFit.CONTAIN,
        border_radius=8,
        visible=False,
    )
    detail_history = ft.Column()
    controller_cards = ft.Column()
    selected_controller_id: str | None = None

    def reset_controller_form():
        nonlocal editing_controller_id, photo_data
        editing_controller_id = None
        controller_name.value = ""
        controller_model.value = ""
        controller_location.value = ""
        controller_note.value = ""
        controller_name.error_text = None
        photo_data = None
        photo_preview.src = ""
        photo_preview.visible = False
        photo_status.value = "写真は選択されていません。"
        photo_error.value = ""
        register_button.visible = True
        save_changes_button.visible = False
        cancel_edit_button.visible = False

    def edit_controller(controller_id: str):
        nonlocal editing_controller_id, photo_data
        controller = next(
            (item for item in load_registry()["controllers"] if item["id"] == controller_id),
            None,
        )
        if controller is None:
            return

        editing_controller_id = controller_id
        controller_name.value = controller["name"]
        controller_name.error_text = None
        controller_model.value = "" if controller.get("model") == "-" else controller.get("model", "")
        controller_location.value = "" if controller.get("location") == "-" else controller.get("location", "")
        controller_note.value = "" if controller.get("note") == "-" else controller.get("note", "")
        photo_data = controller.get("photo_data")
        photo_preview.src = photo_data or ""
        photo_preview.visible = bool(photo_data)
        photo_status.value = "登録済みの写真" if photo_data else "写真は選択されていません。"
        photo_error.value = ""
        register_button.visible = False
        save_changes_button.visible = True
        cancel_edit_button.visible = True
        page.update()

    def cancel_controller_edit(_):
        reset_controller_form()
        page.update()

    def delete_controller(controller_id: str):
        nonlocal selected_controller_id
        data = load_registry()
        controllers = data["controllers"]
        remaining_controllers = [
            controller for controller in controllers if controller["id"] != controller_id
        ]
        if len(remaining_controllers) == len(controllers):
            return

        data["controllers"] = remaining_controllers
        save_registry(data)
        if selected_controller_id == controller_id:
            selected_controller_id = None
            detail_title.value = "コントローラ詳細"
            detail_photo.src = ""
            detail_photo.visible = False
            detail_meta.value = "最新の状態記録を選んでください。"
            detail_history.controls.clear()
        rebuild_controller_list()
        page.update()

    def confirm_delete_controller(controller_id: str, controller_name: str):
        def confirm(_):
            page.pop_dialog()
            delete_controller(controller_id)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("登録情報を削除しますか？"),
                content=ft.Text(
                    f"「{controller_name}」とその記録履歴を削除します。この操作は取り消せません。"
                ),
                actions=[
                    ft.TextButton("キャンセル", on_click=lambda _: page.pop_dialog()),
                    ft.TextButton("削除", on_click=confirm),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def rebuild_controller_list():
        data = load_registry()
        controller_cards.controls.clear()
        if not data["controllers"]:
            controller_cards.controls.append(
                ft.Container(
                    content=ft.Text("まだ登録された制御器がありません。", color="#6A756E"),
                    padding=16,
                    bgcolor="#F8F8F5",
                    border_radius=10,
                )
            )
            return

        for controller in reversed(data["controllers"]):
            history = controller.get("history", [])
            latest = history[-1] if history else {"status": "正常", "score": 100, "summary": "記録なし"}
            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(controller["name"], weight=ft.FontWeight.BOLD, size=18),
                                ft.Container(
                                    content=ft.Text(latest.get("status", "正常"), size=11, weight=ft.FontWeight.BOLD),
                                    padding=ft.Padding(8, 5, 8, 5),
                                    border_radius=8,
                                    bgcolor=status_color(latest.get("status", "正常")) + "22",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(f"機種: {controller.get('model', '-')} | 設置場所: {controller.get('location', '-')}"),
                        ft.Text(f"最新記録: {latest.get('summary', '記録なし')} ({latest.get('score', 0)}点)"),
                        ft.Row(
                            [
                                ft.TextButton(
                                    "詳細を見る",
                                    on_click=lambda e, controller_id=controller["id"]: show_controller_detail(controller_id),
                                ),
                                ft.TextButton(
                                    "変更",
                                    on_click=lambda e, controller_id=controller["id"]: edit_controller(controller_id),
                                ),
                                ft.TextButton(
                                    "削除",
                                    on_click=lambda e, controller_id=controller["id"], name=controller["name"]: confirm_delete_controller(controller_id, name),
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=6,
                ),
                padding=16,
                bgcolor="#FFFFFF",
                border_radius=12,
                border=ft.Border.all(1, "#E5E2D8"),
            )
            controller_cards.controls.append(card)

    def show_controller_detail(controller_id: str):
        nonlocal selected_controller_id
        data = load_registry()
        controller = next((item for item in data["controllers"] if item["id"] == controller_id), None)
        if controller is None:
            selected_controller_id = None
            detail_title.value = "コントローラ詳細"
            detail_photo.src = ""
            detail_photo.visible = False
            detail_meta.value = "対象が見つかりません。"
            detail_history.controls.clear()
            page.update()
            return

        selected_controller_id = controller_id
        latest = controller.get("history", [])[-1] if controller.get("history") else None
        detail_title.value = controller["name"]
        detail_photo.src = controller.get("photo_data") or ""
        detail_photo.visible = bool(controller.get("photo_data"))
        detail_meta.value = (
            f"機種: {controller.get('model', '-')} / 設置場所: {controller.get('location', '-')}"
            f" / 備考: {controller.get('note', '-')}"
        )

        detail_history.controls.clear()
        history = controller.get("history", [])
        if not history:
            detail_history.controls.append(ft.Text("記録がまだありません。診断結果を登録してください。", color="#6E736B"))
        else:
            for entry in reversed(history):
                lines = [
                    ft.Text(entry.get("timestamp", "-"), size=12, color="#5B645F"),
                    ft.Text(entry.get("summary", "記録"), size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"スコア: {entry.get('score', 0)} / 100"),
                ]
                if entry.get("issues"):
                    lines.append(ft.Text("異常:"))
                    lines.extend(ft.Text(f"・{issue}", size=12) for issue in entry.get("issues", []))
                else:
                    lines.append(ft.Text("異常なし"))
                if entry.get("actions"):
                    lines.append(ft.Text("対応:"))
                    lines.extend(ft.Text(f"- {action}", size=12) for action in entry.get("actions", []))

                detail_history.controls.append(
                    ft.Container(
                        content=ft.Column(lines, spacing=5),
                        padding=12,
                        bgcolor="#F7F7F4",
                        border_radius=10,
                        border=ft.Border.all(1, "#E7E4DB"),
                    )
                )
        page.update()

    async def choose_controller_photo(_):
        nonlocal photo_data
        selected_files = await photo_picker.pick_files(
            dialog_title="コントローラーの写真を選択",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
            with_data=True,
            compression_quality=80,
        )
        if not selected_files:
            return

        selected_file = selected_files[0]
        mime_type, _ = mimetypes.guess_type(selected_file.name)
        if mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            photo_error.value = "JPEG、PNG、WebP、GIF形式の写真を選択してください。"
            page.update()
            return
        if not isinstance(selected_file.bytes, bytes):
            photo_error.value = "写真を読み込めませんでした。もう一度選択してください。"
            page.update()
            return

        photo_data = (
            f"data:{mime_type};base64,"
            f"{base64.b64encode(selected_file.bytes).decode('ascii')}"
        )
        photo_preview.src = photo_data
        photo_preview.visible = True
        photo_status.value = f"選択中: {selected_file.name}"
        photo_error.value = ""
        page.update()

    def run_diagnosis(_):
        try:
            voltage = float(voltage_field.value)
        except ValueError:
            summary_text.value = "総合診断: 入力値を確認してください"
            score_text.value = "診断スコア: -"
            issue_list.controls = [ft.Text("電圧の入力が数値ではありません。", color="#B24A36")]
            advice_text.value = "電源電圧を数値で入力してください。"
            page.update()
            return

        score, status, issues, actions = diagnose_wiring(
            voltage=voltage,
            ground_ok=not ground_fault_checkbox.value,
            signal_state=[
                state
                for checkbox, state in [
                    (signal_break_checkbox, "断線"),
                    (signal_short_checkbox, "短絡"),
                    (signal_noise_checkbox, "ノイズあり"),
                ]
                if checkbox.value
            ],
            connector_state=[
                state
                for checkbox, state in [
                    (connector_loose_checkbox, "ゆるい"),
                    (contact_failure_checkbox, "接触不良"),
                    (connector_corrosion_checkbox, "腐食"),
                ]
                if checkbox.value
            ],
            heat_state=[
                state
                for checkbox, state in [
                    (heat_moderate_checkbox, "やや高い"),
                    (heat_high_checkbox, "高い"),
                ]
                if checkbox.value
            ],
            noise_state="発生" if noise_checkbox.value else "なし",
            cable_length="長い" if cable_long_checkbox.value else "標準",
        )

        summary_text.value = f"総合診断: {status}"
        score_text.value = f"診断スコア: {score} / 100"
        issue_list.controls = [ft.Text(f"・{issue}", size=14) for issue in issues] or [ft.Text("・異常は見当たりません。", size=14)]
        advice_text.value = "\n".join(actions)
        summary_text.color = status_color(status)
        score_text.color = status_color(status)
        page.update()

    def register_controller(_):
        nonlocal photo_data
        name = controller_name.value.strip()
        if not name:
            controller_name.error_text = "制御器名を入力してください。"
            page.update()
            return

        controller_name.error_text = None

        if editing_controller_id is not None:
            data = load_registry()
            controller = next(
                (item for item in data["controllers"] if item["id"] == editing_controller_id),
                None,
            )
            if controller is None:
                controller_name.error_text = "変更する制御器が見つかりません。"
                page.update()
                return

            controller["name"] = name
            controller["model"] = controller_model.value.strip() or "-"
            controller["location"] = controller_location.value.strip() or "-"
            controller["note"] = controller_note.value.strip() or "-"
            controller["photo_data"] = photo_data
            save_registry(data)
            controller_id = editing_controller_id
            reset_controller_form()
            rebuild_controller_list()
            show_controller_detail(controller_id)
            page.update()
            return

        try:
            voltage = float(voltage_field.value)
            signal_state = [
                state
                for checkbox, state in [
                    (signal_break_checkbox, "断線"),
                    (signal_short_checkbox, "短絡"),
                    (signal_noise_checkbox, "ノイズあり"),
                ]
                if checkbox.value
            ]
            connector_state = [
                state
                for checkbox, state in [
                    (connector_loose_checkbox, "ゆるい"),
                    (contact_failure_checkbox, "接触不良"),
                    (connector_corrosion_checkbox, "腐食"),
                ]
                if checkbox.value
            ]
            heat_state = [
                state
                for checkbox, state in [
                    (heat_moderate_checkbox, "やや高い"),
                    (heat_high_checkbox, "高い"),
                ]
                if checkbox.value
            ]
            score, status, issues, actions = diagnose_wiring(
                voltage=voltage,
                ground_ok=not ground_fault_checkbox.value,
                signal_state=signal_state,
                connector_state=connector_state,
                heat_state=heat_state,
                noise_state="発生" if noise_checkbox.value else "なし",
                cable_length="長い" if cable_long_checkbox.value else "標準",
            )
        except ValueError:
            controller_name.error_text = "診断入力の電圧が正しくありません。"
            page.update()
            return

        data = load_registry()
        controller = {
            "id": str(uuid4()),
            "name": name,
            "model": controller_model.value.strip() or "-",
            "location": controller_location.value.strip() or "-",
            "note": controller_note.value.strip() or "-",
            "photo_data": photo_data,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "history": [
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": status,
                    "summary": f"{status}（{score}点）",
                    "score": score,
                    "issues": issues,
                    "actions": actions,
                    "voltage": voltage,
                    "ground_ok": not ground_fault_checkbox.value,
                    "signal_state": signal_state,
                    "connector_state": connector_state,
                    "heat_state": heat_state,
                    "noise_state": "発生" if noise_checkbox.value else "なし",
                    "cable_length": "長い" if cable_long_checkbox.value else "標準",
                }
            ],
        }

        data["controllers"].append(controller)
        save_registry(data)

        reset_controller_form()
        rebuild_controller_list()
        show_controller_detail(controller["id"])
        page.update()

    left_panel = ft.Column(
        [
            ft.Text("診断入力", size=22, weight=ft.FontWeight.BOLD),
            ft.Column(
                [
                    ft.Text("コントローラーの配線", weight=ft.FontWeight.BOLD),
                    voltage_field,
                    ground_fault_checkbox,
                    signal_break_checkbox,
                    signal_short_checkbox,
                    signal_noise_checkbox,
                    connector_loose_checkbox,
                    contact_failure_checkbox,
                    connector_corrosion_checkbox,
                    cable_long_checkbox,
                    ft.Text("コントローラー関連", weight=ft.FontWeight.BOLD),
                    heat_moderate_checkbox,
                    heat_high_checkbox,
                    noise_checkbox,
                ],
                spacing=10,
            ),
            ft.Button("診断を実行", on_click=run_diagnosis, icon=ft.Icons.INSIGHTS_OUTLINED),
            ft.Container(
                content=ft.Column(
                    [
                        summary_text,
                        score_text,
                        ft.Divider(),
                        ft.Text("主な異常項目", weight=ft.FontWeight.BOLD),
                        issue_list,
                        ft.Divider(),
                        ft.Text("推奨対応", weight=ft.FontWeight.BOLD),
                        advice_text,
                    ],
                    spacing=8,
                ),
                padding=16,
                bgcolor="#FFFFFF",
                border_radius=12,
                border=ft.Border.all(1, "#E1DED3"),
            ),
        ],
        spacing=16,
        width=500,
    )

    history_panel = ft.Container(
        content=ft.Column(
            [
                detail_title,
                detail_photo,
                detail_meta,
                detail_history,
            ],
            spacing=10,
        ),
        padding=16,
        bgcolor="#FFFFFF",
        border_radius=12,
        border=ft.Border.all(1, "#E1DED3"),
    )

    right_panel = ft.Column(
        [
            ft.Text("制御器登録", size=22, weight=ft.FontWeight.BOLD),
            ft.Column(
                [
                    controller_name,
                    controller_model,
                    controller_location,
                    controller_note,
                    ft.Row(
                        [
                            ft.Button(
                                "写真を選択",
                                on_click=choose_controller_photo,
                                icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                            ),
                            photo_status,
                        ],
                        wrap=True,
                    ),
                    photo_preview,
                    photo_error,
                ],
                spacing=10,
            ),
            register_button,
            save_changes_button,
            cancel_edit_button,
            ft.Text("登録済み制御器一覧", size=20, weight=ft.FontWeight.BOLD),
            controller_cards,
            history_panel,
        ],
        spacing=14,
        width=500,
    )

    register_button.on_click = register_controller
    save_changes_button.on_click = register_controller
    cancel_edit_button.on_click = cancel_controller_edit

    rebuild_controller_list()
    controllers = load_registry()["controllers"]
    if controllers:
        show_controller_detail(controllers[-1]["id"])

    page.add(
        ft.Column(
            [
                ft.Text("コントローラ配線チェックシート", size=30, weight=ft.FontWeight.BOLD),
                ft.Text("制御器を登録し、その状態を時系列で記録・確認できます。", size=14, color="#5A655D"),
                ft.Row([left_panel, right_panel], spacing=20, vertical_alignment=ft.CrossAxisAlignment.START),
            ],
            spacing=22,
        )
    )


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8555)