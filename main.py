import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import flet as ft


DATA_FILE = Path.home() / ".controller_wiring_registry.json"


def diagnose_wiring(
    voltage: float,
    ground_ok: bool,
    signal_state: str,
    connector_state: str,
    heat_state: str,
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

    if signal_state == "断線":
        score -= 35
        issues.append("信号線に断線の可能性があります。")
        actions.append("各信号ラインを途中でチェックし、コネクタと端子を点検してください。")
    elif signal_state == "短絡":
        score -= 40
        issues.append("信号線が短絡している可能性があります。")
        actions.append("短絡箇所を特定し、絶縁や配線ルートを見直してください。")
    elif signal_state == "ノイズあり":
        score -= 20
        issues.append("ノイズが混入している可能性があります。")
        actions.append("配線の束ね方を見直し、ハーネスの分離とシールド対策を検討してください。")

    if connector_state == "ゆるい":
        score -= 18
        issues.append("コネクタが緩んでいます。")
        actions.append("コネクタの固定、端子の圧着、ロック機構を確認してください。")
    elif connector_state == "腐食":
        score -= 25
        issues.append("コネクタの腐食が見られます。")
        actions.append("接点の清掃または交換を行い、保護カバーの設置を検討してください。")

    if heat_state == "高い":
        score -= 25
        issues.append("配線または端子の発熱が大きいです。")
        actions.append("負荷状況と接触抵抗を確認し、過負荷や断線がないかを検査してください。")
    elif heat_state == "やや高い":
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

    controller_name = ft.TextField(label="制御器名", width=240)
    controller_model = ft.TextField(label="機種名 / 型番", width=240)
    controller_location = ft.TextField(label="設置場所", width=240)
    controller_note = ft.TextField(label="備考", multiline=True, min_lines=3, max_lines=5, width=500)

    voltage_field = ft.TextField(label="電源電圧（V）", value="12.0", width=220)
    ground_dropdown = ft.Dropdown(
        label="グランド接続",
        width=220,
        options=[
            ft.dropdown.Option("正常"),
            ft.dropdown.Option("不良"),
        ],
        value="正常",
    )
    signal_dropdown = ft.Dropdown(
        label="信号線状態",
        width=220,
        options=[
            ft.dropdown.Option("正常"),
            ft.dropdown.Option("断線"),
            ft.dropdown.Option("短絡"),
            ft.dropdown.Option("ノイズあり"),
        ],
        value="正常",
    )
    connector_dropdown = ft.Dropdown(
        label="コネクタ状態",
        width=220,
        options=[
            ft.dropdown.Option("良好"),
            ft.dropdown.Option("ゆるい"),
            ft.dropdown.Option("腐食"),
        ],
        value="良好",
    )
    heat_dropdown = ft.Dropdown(
        label="発熱状態",
        width=220,
        options=[
            ft.dropdown.Option("正常"),
            ft.dropdown.Option("やや高い"),
            ft.dropdown.Option("高い"),
        ],
        value="正常",
    )
    noise_dropdown = ft.Dropdown(
        label="誤動作 / ノイズ",
        width=220,
        options=[
            ft.dropdown.Option("なし"),
            ft.dropdown.Option("発生"),
        ],
        value="なし",
    )
    length_dropdown = ft.Dropdown(
        label="配線長",
        width=220,
        options=[
            ft.dropdown.Option("標準"),
            ft.dropdown.Option("長い"),
        ],
        value="標準",
    )

    summary_text = ft.Text("総合診断: まだ診断していません", size=20, weight=ft.FontWeight.BOLD)
    score_text = ft.Text("診断スコア: 0 / 100", size=16, color="#2F3B2F")
    issue_list = ft.Column()
    advice_text = ft.Text("診断結果がここに表示されます。", size=14, color="#4E584D")

    detail_title = ft.Text("コントローラ詳細", size=22, weight=ft.FontWeight.BOLD)
    detail_meta = ft.Text("最新の状態記録を選んでください。", size=13, color="#59635D")
    detail_history = ft.Column()
    controller_cards = ft.Column()

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
                        ft.TextButton("詳細を見る", on_click=lambda e, controller_id=controller["id"]: show_controller_detail(controller_id)),
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
        data = load_registry()
        controller = next((item for item in data["controllers"] if item["id"] == controller_id), None)
        if controller is None:
            detail_title.value = "コントローラ詳細"
            detail_meta.value = "対象が見つかりません。"
            detail_history.controls.clear()
            page.update()
            return

        latest = controller.get("history", [])[-1] if controller.get("history") else None
        detail_title.value = controller["name"]
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
            ground_ok=ground_dropdown.value == "正常",
            signal_state=signal_dropdown.value,
            connector_state=connector_dropdown.value,
            heat_state=heat_dropdown.value,
            noise_state=noise_dropdown.value,
            cable_length=length_dropdown.value,
        )

        summary_text.value = f"総合診断: {status}"
        score_text.value = f"診断スコア: {score} / 100"
        issue_list.controls = [ft.Text(f"・{issue}", size=14) for issue in issues] or [ft.Text("・異常は見当たりません。", size=14)]
        advice_text.value = "\n".join(actions)
        summary_text.color = status_color(status)
        score_text.color = status_color(status)
        page.update()

    def register_controller(_):
        name = controller_name.value.strip()
        if not name:
            controller_name.error_text = "制御器名を入力してください。"
            page.update()
            return

        controller_name.error_text = None

        try:
            voltage = float(voltage_field.value)
            score, status, issues, actions = diagnose_wiring(
                voltage=voltage,
                ground_ok=ground_dropdown.value == "正常",
                signal_state=signal_dropdown.value,
                connector_state=connector_dropdown.value,
                heat_state=heat_dropdown.value,
                noise_state=noise_dropdown.value,
                cable_length=length_dropdown.value,
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
                    "ground_ok": ground_dropdown.value == "正常",
                    "signal_state": signal_dropdown.value,
                    "connector_state": connector_dropdown.value,
                    "heat_state": heat_dropdown.value,
                    "noise_state": noise_dropdown.value,
                    "cable_length": length_dropdown.value,
                }
            ],
        }

        data["controllers"].append(controller)
        save_registry(data)

        controller_name.value = ""
        controller_model.value = ""
        controller_location.value = ""
        controller_note.value = ""
        rebuild_controller_list()
        show_controller_detail(controller["id"])
        page.update()

    left_panel = ft.Column(
        [
            ft.Text("診断入力", size=22, weight=ft.FontWeight.BOLD),
            ft.Column(
                [
                    voltage_field,
                    ground_dropdown,
                    signal_dropdown,
                    connector_dropdown,
                    heat_dropdown,
                    noise_dropdown,
                    length_dropdown,
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

    right_panel = ft.Column(
        [
            ft.Text("制御器登録", size=22, weight=ft.FontWeight.BOLD),
            ft.Column(
                [
                    controller_name,
                    controller_model,
                    controller_location,
                    controller_note,
                ],
                spacing=10,
            ),
            ft.Button("登録して状態を記録", on_click=register_controller, icon=ft.Icons.SAVE_ALT_ROUNDED),
            ft.Text("登録済み制御器一覧", size=20, weight=ft.FontWeight.BOLD),
            controller_cards,
        ],
        spacing=14,
        width=500,
    )

    history_panel = ft.Container(
        content=ft.Column(
            [
                detail_title,
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
                history_panel,
            ],
            spacing=22,
        )
    )


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8555)