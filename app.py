# -*- coding: utf-8 -*-
import streamlit as st
from streamlit_mic_recorder import mic_recorder
from openai import OpenAI
import time, json, io, wave, struct, math, os

# ==========================================
# 提案力道場 v3 - 設定
# ==========================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# 効果音システム（Python WAV生成 → st.audio autoplay）
# ==========================================
def generate_wav(notes, wave_type='square', volume=0.35, sample_rate=22050):
    """チップチューン風の効果音をWAVバイト列として生成する"""
    samples = []
    for freq, dur in notes:
        n = int(sample_rate * dur)
        for i in range(n):
            t = i / sample_rate
            if freq <= 0:
                v = 0.0
            elif wave_type == 'square':
                v = volume if math.sin(2 * math.pi * freq * t) >= 0 else -volume
            elif wave_type == 'triangle':
                p = (t * freq) % 1.0
                v = volume * (4.0 * abs(p - 0.5) - 1.0)
            elif wave_type == 'sawtooth':
                p = (t * freq) % 1.0
                v = volume * (2.0 * p - 1.0)
            else:
                v = volume if math.sin(2 * math.pi * freq * t) >= 0 else -volume
            left = n - i
            if left < 100:
                v *= left / 100.0
            samples.append(max(-1.0, min(1.0, v)))

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for s in samples:
            w.writeframes(struct.pack('<h', int(s * 32767)))
    buf.seek(0)
    return buf.read()

SOUND_DEFS = {
    "start":     ([(523,0.12),(659,0.12),(784,0.12),(1047,0.25)], "square"),
    "encounter": ([(220,0.08),(277,0.08),(330,0.08),(0,0.06),(220,0.08),(277,0.08),(330,0.08),(440,0.18)], "square"),
    "select":    ([(880,0.06),(1109,0.10)], "square"),
    "hint":      ([(587,0.12),(784,0.12),(988,0.20)], "triangle"),
    "battle":    ([(440,0.10),(554,0.10),(659,0.10),(880,0.25)], "sawtooth"),
    "result_s":  ([(523,0.09),(523,0.09),(0,0.09),(523,0.09),(0,0.09),(415,0.09),(523,0.09),(0,0.09),(659,0.18),(0,0.09),(330,0.18)], "square"),
    "result_a":  ([(523,0.15),(659,0.15),(784,0.30)], "square"),
    "result_b":  ([(392,0.20),(440,0.30)], "triangle"),
    "result_c":  ([(311,0.25),(262,0.35)], "triangle"),
    "levelup":   ([(523,0.07),(587,0.07),(659,0.07),(698,0.07),(784,0.07),(880,0.07),(988,0.07),(1047,0.20)], "square"),
    "ending":    ([(523,0.16),(659,0.16),(784,0.16),(1047,0.32),(784,0.12),(880,0.12),(1047,0.40)], "square"),
    "secret":    ([(784,0.10),(988,0.10),(1175,0.10),(0,0.05),(784,0.10),(988,0.10),(1175,0.10),(0,0.05),(1047,0.12),(1175,0.12),(1319,0.12),(1047,0.40)], "triangle"),
}

@st.cache_data
def get_wav(name):
    if name not in SOUND_DEFS:
        return None
    notes, wt = SOUND_DEFS[name]
    return generate_wav(notes, wt)

def play_sound(name):
    data = get_wav(name)
    if data:
        st.audio(data, format="audio/wav", autoplay=True)

# ==========================================
# ゲーム設定
# ==========================================
LEVELS = {
    1: {"name": "お客様の課長", "emoji": "👔", "perspective": "現場"},
    2: {"name": "お客様の部長", "emoji": "🎩", "perspective": "部門"},
    3: {"name": "お客様の経営層", "emoji": "👑", "perspective": "全社"},
}

THEMES = {
    "DX": {
        "title": "⚡ DX（デジタルの光）",
        "situation": {
            1: "製造部の検査工程で、検査員の田中さんが紙の検査記録シートに手書きで記入し、終業後にExcelへ転記している。1日あたり約1.5時間を転記作業に費やしており、先月は転記ミスが3件発生、うち1件は出荷後に顧客クレームに発展した。課長は「田中さんの本来の業務時間が削られている上に、データの信頼性も担保できない」と頭を抱えている。",
            2: "営業部と生産管理部がメールとExcelで受注情報をやり取りしており、先月は仕様変更の伝達漏れにより30台を誤生産、手戻りコスト150万円が発生した。部長は「受注から生産までの情報が一元化されていないのが根本原因だ」と問題視している。",
            3: "競合のS社が受注から生産計画まで一気通貫でデジタル化し、見積回答を即日化。当社は平均5営業日かかっており、今期の相見積もりでS社に負けた案件が前年比8件増加、失注額は推定4,000万円。営業本部からは「スピードで負けている」と報告が相次いでいる。",
        },
        "mission": {
            1: "👔 検査工程の転記問題を解決する打ち手を、30秒でお客様の課長に提案せよ。",
            2: "🎩 受注から生産までの情報連携を改善する方法を、30秒でお客様の部長に提案せよ。",
            3: "👑 見積回答スピードで競合に勝つ戦略を、30秒でお客様の経営層に提案せよ。",
        },
        "core_info": {
            1: "田中さん / 1.5時間/日 / ミス3件 / 顧客クレーム1件",
            2: "30台誤生産 / 150万円 / メールとExcel / 情報の一元化",
            3: "S社 / 即日 vs 5営業日 / 8件増 / 4,000万円",
        },
        "hints": [
            "【第1のヒント：フックの極意】\n最初の一文で相手の痛みを掴め。「課長、田中さんの転記作業の件ですが」と切り出すだけで、相手は「わかってくれている」と感じる。シチュエーションの固有名詞（人名・数値）を最初の一文に入れよう。",
            "【第2のヒント：施策の磨き方】\n「デジタル化」「見える化」はバズワード。師匠は認めぬ。\n具体的なツール名・仕組み名を使え：\n・悪い例：「デジタル化します」\n・良い例：「タブレット端末での直接入力に切り替えます」\n1〜2つの施策を深く語る方が、浅い3つより刺さる。",
            "【第3のヒント：30秒テンプレート】\n「【フック】○○課長、（固有名詞＋数値）の件ですが、（相手の痛み）かと存じます。\n【施策】ご提案は、（具体的な施策名）の導入です。（補足1文）\n【着地】これにより（定量効果）を実現し、（状態変化）いたします。」\n\n例）課長向け：\n「課長、田中さんが毎日1.5時間かけている転記作業の件ですが、先月のミス3件は深刻です。ご提案はタブレット端末での現場直接入力です。規格外の値には自動アラートも設定します。転記作業ゼロ、ミスによるクレームを根絶します。」",
        ],
    },
    "コスト削減": {
        "title": "💰 コスト削減（黄金の節約）",
        "situation": {
            1: "製造ラインの段取り替えに毎回45分かかり、年間で約800時間の稼働ロスが発生している。ベテランの鈴木さんだけが速く段取りできるが、マニュアルがないため他のメンバーでは時間が1.5倍かかる。課長は「鈴木さんが休むとラインが回らない」と不安を感じている。",
            2: "主要部品のサプライヤー5社に対し、担当者ごとにバラバラの価格交渉をしており、同じ部品でも単価が最大15%異なっている。年間調達額3億円のうち、集約・統一により年間2,000万円の削減余地があるが、改革が進んでいない。",
            3: "売上総利益率が28%と業界平均の35%を7ポイント下回っており、中期経営計画の目標33%に対して初年度の改善はわずか0.5ポイント。主因は設備稼働率の低さと外注加工費の高止まりにある。経営会議では「構造的にコスト体質を変えなければ成長投資の原資が確保できない」と議論されている。",
        },
        "mission": {
            1: "👔 段取り替えのロスを削減する打ち手を、30秒でお客様の課長に提案せよ。",
            2: "🎩 調達コストの構造的な削減方法を、30秒でお客様の部長に提案せよ。",
            3: "👑 利益率を改善する構造改革の方向性を、30秒でお客様の経営層に提案せよ。",
        },
        "core_info": {
            1: "45分/回 / 800時間/年 / 鈴木さん / 1.5倍",
            2: "5社 / 単価差15% / 3億円 / 2,000万円削減余地",
            3: "28% vs 35% / 目標33% / 初年度+0.5pt / 成長投資の原資",
        },
        "hints": [
            "【第1のヒント：フックの極意】\n「コスト削減しましょう」では相手の心は動かない。\n相手が今まさに感じている痛みを、固有名詞と数値で言語化せよ。\n・課長なら：「鈴木さんが休むとラインが止まる不安」\n・部長なら：「同じ部品で15%も単価が違う理不尽さ」\n・経営層なら：「業界平均から7ポイント離された焦り」",
            "【第2のヒント：施策の磨き方】\n30秒で語れる施策は1〜2つが限界。最も効果の大きい打ち手を選べ。\n・悪い例：「効率化します」「最適化を図ります」\n・良い例：「鈴木さんの段取り手順を動画撮影してビジュアルマニュアルを作成します」\n聞いた相手が「来週から始められそうだ」と思える具体度を目指せ。",
            "【第3のヒント：30秒テンプレート】\n「【フック】○○部長、（固有名詞＋数値）の件ですが、（相手の痛み）かと存じます。\n【施策】ご提案は（具体的な施策名）です。（補足1文）\n【着地】これにより（定量効果）を実現いたします。」\n\n例）部長向け：\n「部長、5社のサプライヤーで同じ部品の単価が最大15%違っているのは、年間3億円の調達に対して大きなロスです。品目ごとの単価比較データベースを構築し、スコアカード制で評価を一本化します。初年度で1,500万円の削減を実現いたします。」",
        ],
    },
    "納期遅延": {
        "title": "⏰ 納期遅延（運命の時計）",
        "situation": {
            1: "先月、主要顧客のA社（年間取引額5,000万円）への納品が10日遅延した。原因は生産管理担当の佐藤さんがインフルエンザで1週間不在となり、部品の発注タイミングを逃したこと。佐藤さん以外に発注業務を担えるメンバーがいなかった。A社からは「佐藤さんがいないと回らないのか。次回は取引見直し」と警告されている。",
            2: "今四半期で納期遅延が4件発生した。いずれも調達部の入荷遅れが製造部・品質管理部に波及する同じパターン。原因は部門ごとの管理方法がバラバラ（Excel・ホワイトボード・紙台帳）で、遅延情報がリアルタイムに共有されないこと。部長は「個々の部門は頑張っているが、つなぎ目で毎回遅れる」と認識している。",
            3: "納期遵守率が91%にとどまり、競合H社の98%に大きく劣後している。その結果、主要顧客のF社（年間1.2億円）から「遵守率95%以上が次回契約の条件」と通告され、G社（年間1.5億円）は既にH社への切り替えを始めている。合計2.7億円の売上を守るために、今期中の遵守率改善が急務。",
        },
        "mission": {
            1: "👔 属人化による納期遅延を防ぐ仕組みを、30秒でお客様の課長に提案せよ。",
            2: "🎩 部門間の遅延連鎖を止める方法を、30秒でお客様の部長に提案せよ。",
            3: "👑 顧客の信頼を回復し契約を守る戦略を、30秒でお客様の経営層に提案せよ。",
        },
        "core_info": {
            1: "A社 / 5,000万円 / 10日遅延 / 佐藤さん / 取引見直し",
            2: "4件 / 同じパターン / Excel・ホワイトボード・紙台帳 / つなぎ目",
            3: "91% vs H社98% / F社1.2億 / G社1.5億 / 2.7億円リスク / 95%条件",
        },
        "hints": [
            "【第1のヒント：フックの極意】\nお客様が最も恐れていることを、最初の一文で言い当てよ。\n・課長：「A社様の5,000万円のお取引を失うこと」\n・部長：「また同じパターンで遅延が起きること」\n・経営層：「F社様・G社様の合計2.7億円が流出すること」\n恐れを言語化された相手は「この人はわかっている」と信頼する。",
            "【第2のヒント：施策の磨き方】\nお客様への提案では、「御社は〜すべき」より「弊社がご提案するのは〜です」が刺さる。\n・悪い例：「属人化を解消してください」\n・良い例：「佐藤さんの発注業務を工程分解したデジタルマニュアルの作成をご提案します」\n施策はお客様が「それならやってみたい」と思える具体度を目指せ。",
            "【第3のヒント：30秒テンプレート】\n「【フック】○○課長、（固有名詞＋数値）の件ですが、（相手の痛み）かと存じます。\n【施策】弊社からのご提案は（具体的な施策名）です。（補足1文）\n【着地】これにより（定量効果）を実現し、（状態変化）いたします。」\n\n例）課長向け：\n「課長、A社様への10日遅延の件ですが、5,000万円のお取引先から『次は見直し』と言われている以上、急務です。佐藤さんの発注業務のデジタルマニュアル作成と、副担当をつけるペア制をご提案します。佐藤さんが不在でも発注が止まらない体制を実現します。」",
        ],
    },
}

# ==========================================
# 音声認識（Whisper）
# ==========================================
def transcribe_whisper(audio_bytes):
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, language="ja", response_format="text"
        )
        return transcript
    except Exception as e:
        st.error(f"音声認識エラー: {e}")
        return ""

# ==========================================
# 師匠の評価（2ステップ Chain-of-Thought）
# ==========================================
def evaluate_pitch(level, theme, transcript):
    li = LEVELS[level]
    ti = THEMES[theme]

    # ── STEP 1: 発言から証拠を引用させる ──────────────────
    step1_prompt = f"""あなたは採点官です。以下の弟子の発言を読み、各項目について発言中から該当する表現を「そのまま引用」してください。

【弟子の発言】
{transcript}

【シチュエーション（参考）】
{ti['situation'][level]}
核心情報: {ti['core_info'][level]}

以下のJSON形式で、各項目の引用を返してください。該当する表現がなければ「なし」と書いてください。
{{
  "hook_quote": "フック・課題把握に該当する発言の引用（固有名詞・数値・相手の痛みを示す箇所）",
  "measure_quote": "施策の具体性に該当する発言の引用（何を・どうするかの動作を示す箇所）",
  "evidence_quote": "根拠・数値の活用に該当する発言の引用（固有名詞・数値・データを示す箇所）",
  "landing_quote": "着地・効果に該当する発言の引用（定量効果・状態変化を示す箇所）"
}}"""

    step1_result = None
    for attempt in range(3):
        try:
            resp1 = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "発言から該当箇所を引用するだけです。必ずJSON形式のみで返答してください。"},
                    {"role": "user", "content": step1_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            step1_result = json.loads(resp1.choices[0].message.content.strip())
            break
        except Exception as e:
            err_str = str(e)
            if ('429' in err_str or 'rate_limit' in err_str.lower()) and attempt < 2:
                time.sleep((attempt + 1) * 10)
                continue
            return {"score":0,"rank":"C","hook_score":0,"measure_score":0,
                    "evidence_score":0,"landing_score":0,
                    "good_points":"Step1でエラーが発生した。",
                    "improvements":"もう一度挑戦せよ。",
                    "next_tips":"再度試してみよ。",
                    "comment":f"エラー: {e}"}

    # ── STEP 2: 引用した証拠をもとに採点させる ────────────
    step2_prompt = f"""あなたは提案力道場の師匠です。採点官が引用した証拠をもとに、以下のルールで採点してください。

【採点対象の発言】
{transcript}

【採点官が引用した証拠】
- フック（固有名詞・数値・相手の痛み）: {step1_result.get('hook_quote','なし')}
- 施策（何を・どうするかの動作）: {step1_result.get('measure_quote','なし')}
- 根拠（固有名詞・数値・データ）: {step1_result.get('evidence_quote','なし')}
- 着地（定量効果・状態変化）: {step1_result.get('landing_quote','なし')}

【採点ルール（各25点・6段階）＋境界判定の具体例】

■ フック（引用: {step1_result.get('hook_quote','なし')}）
- 25点: 固有名詞＋数値＋お客様目線の言い換えがすべて揃っている
  　例○「部長、今四半期4件の遅延、調達部の入荷遅れが製造部・品管部へ波及する同じパターンです」
- 20点: 固有名詞・数値は使っているがお客様目線の言い換えが弱い（「〜とお聞きしています」止まりなど）
  　例○「S社に負けて今期4,000万円の失注が出ているとお聞きしています」← 数値はあるが相手の痛みの言い換えが薄い
- 15点: 課題の方向性は合っているが固有名詞・数値がない
- 10点: 一般的な課題認識
- 5点: 課題の特定が曖昧
- 0点: フックなし

■ 施策（引用: {step1_result.get('measure_quote','なし')}）
- 25点: 「何を対象に・何をすると・何が起きる」という動作の流れが明確に示されている
  　例○「3部門の進捗を一画面で管理し、入荷遅れが発生した瞬間に全部門へ即時通知が届く仕組み」
  　例○「標準品の仕様を入力すると自動で見積書が生成される仕組み」
- 20点: 解決の方向性と対象は明確だが、「何が起きるか」の動作の結果がやや薄い
- 15点: 「〜を自動化する」「〜を進める」など、やりたいことの方向性は伝わるが具体的な動作・仕組みが不明確
  　例×「見積の自動化を進めれば大幅に短縮できます。まずは標準品から着手」← 何をどう自動化するかが不明
- 10点: 「見える化」「効率化」などバズワードのみで動作説明なし
- 5点: 一般論
- 0点: 施策への言及なし

■ 根拠（引用: {step1_result.get('evidence_quote','なし')}）
- 25点: 固有名詞・数値が2種類以上あり、かつそれぞれが提案内容と直接つながっている
  　例○「Excel・ホワイトボード・紙台帳のバラバラな管理（原因）→ 一元化の提案（解決）」のように因果がつながっている
- 20点: 固有名詞・数値が複数あるが、提案との因果のつながりが「大幅に短縮できます」など一言で済んでいて薄い
  　例△「S社／4,000万円／5営業日」は3つあるが「自動化すれば短縮できる」とだけ述べており因果が弱い
- 15点: 状況に触れているが固有名詞・数値がない
- 10点: 言及が一般的
- 5点: ほぼ触れていない
- 0点: 完全に一般論

■ 着地（引用: {step1_result.get('landing_quote','なし')}）
- 25点: 定量的効果（数値）＋具体的な状態変化（何がどう変わるか）の両方が明示されている
  　例○「つなぎ目の遅れをゼロ（状態変化）＋来四半期の遅延0件（定量効果）」
- 20点: 定量的数値 OR 状態変化のどちらか一方のみ
  　例△「来期までに2営業日以内を目指す」← 数値目標はあるが状態変化（何がどう変わるか）の記述がない
- 15点: 効果の方向性はあるが数値も状態変化も曖昧
- 10点: 漠然と効果に触れている
- 5点: 効果がほぼ不明
- 0点: 効果への言及なし

【重要ルール】
- 引用が「なし」の項目は0〜5点とせよ
- 引用がある項目は、その引用内容を上記ルールに照らして機械的に採点せよ
- 印象・全体感・「なんとなく」での減点は禁止
- scoreはhook_score + measure_score + evidence_score + landing_scoreの合計と必ず一致させよ
- rankはS(90-100) / A(70-89) / B(50-69) / C(0-49)

以下のJSON形式のみで返してください：
{{
  "score": 合計点数（0-100の整数）,
  "rank": "S/A/B/C",
  "hook_score": フックの点数（0/5/10/15/20/25のみ）,
  "measure_score": 施策の点数（0/5/10/15/20/25のみ）,
  "evidence_score": 根拠の点数（0/5/10/15/20/25のみ）,
  "landing_score": 着地の点数（0/5/10/15/20/25のみ）,
  "good_points": "引用を使って良かった点を具体的に（100文字程度）",
  "improvements": "30秒で使えるフレーズを例示して改善提案（100文字程度）",
  "next_tips": "次回使うべき固有名詞・数値・言い換え例を明示（100文字程度）",
  "comment": "師匠の温かい励まし（50文字程度）"
}}"""

    for attempt in range(3):
        try:
            resp2 = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "引用された証拠をもとに採点し、必ずJSON形式のみで返答してください。"},
                    {"role": "user", "content": step2_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            cj = resp2.choices[0].message.content.strip()
            r = json.loads(cj)
            # score と各項目の合計が一致しない場合は再計算
            calc = (r.get('hook_score',0) + r.get('measure_score',0)
                    + r.get('evidence_score',0) + r.get('landing_score',0))
            r['score'] = calc
            if calc >= 90:   r['rank'] = 'S'
            elif calc >= 70: r['rank'] = 'A'
            elif calc >= 50: r['rank'] = 'B'
            else:            r['rank'] = 'C'
            return r
        except Exception as e:
            err_str = str(e)
            if ('429' in err_str or 'rate_limit' in err_str.lower()) and attempt < 2:
                wait = (attempt + 1) * 10
                st.toast(f"⏳ APIが混み合っています。{wait}秒後に再試行します…")
                time.sleep(wait)
                continue
            return {"score":0,"rank":"C","hook_score":0,"measure_score":0,
                    "evidence_score":0,"landing_score":0,
                    "good_points":"システムエラーが発生した。",
                    "improvements":"もう一度挑戦せよ。",
                    "next_tips":"再度試してみよ。",
                    "comment":f"エラー: {e}"}

# ==========================================
# 時間フォーマット
# ==========================================
def fmt_time(seconds):
    """秒数を mm:ss 形式に変換"""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

# ==========================================
# CSS
# ==========================================
def load_css():
    st.markdown("""<style>
    audio { display: none; }

    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
    .main{background:linear-gradient(135deg,#1e3a8a 0%,#312e81 100%);color:#fff}
    .stButton>button{background:linear-gradient(180deg,#fbbf24,#f59e0b);color:#000;
      border:3px solid #fff;font-weight:bold;font-size:18px;padding:12px 24px;
      border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,.3);min-height:80px;white-space:normal}
    .stButton>button:hover{background:linear-gradient(180deg,#fcd34d,#fbbf24);transform:translateY(-2px)}
    h1,h2,h3{text-shadow:2px 2px 4px rgba(0,0,0,.8)}
    .village-elder{background:rgba(0,0,0,.6);border:3px solid #fbbf24;border-radius:12px;padding:20px;margin:20px 0}
    .timer-box{font-size:40px;font-weight:bold;color:#4ade80;text-align:center;
      text-shadow:3px 3px 6px rgba(0,0,0,.8);background:rgba(0,0,0,.5);
      border:2px solid #4ade80;border-radius:8px;padding:10px;margin:10px 0}
    .timer-label{font-size:13px;color:#a3e635;text-align:center;margin-bottom:4px;font-weight:bold}
    .timer-stopped{color:#fbbf24 !important;border-color:#fbbf24 !important}
    .dragon-quest-box{background:#000;border:4px solid #fff;padding:30px 40px;margin:20px 0;
      font-family:'Press Start 2P',cursive;font-size:24px;color:#fff;text-shadow:3px 3px 0 #000;
      line-height:2.2;box-shadow:0 8px 16px rgba(0,0,0,.8);text-align:center}
    .core-info-box{background:rgba(251,191,36,.15);border:2px solid #fbbf24;
      border-radius:8px;padding:12px 16px;margin:10px 0;font-size:14px}
    .time-record-box{background:rgba(74,222,128,.1);border:2px solid #4ade80;
      border-radius:8px;padding:12px 16px;margin:10px 0;font-size:15px}
    .secret-btn>button{background:linear-gradient(180deg,#1e3a8a,#312e81) !important;
      color:#1e3a8a !important;border:1px solid #1e3a8a !important;
      font-size:8px !important;min-height:20px !important;padding:2px 4px !important;
      box-shadow:none !important;opacity:0.15}
    .secret-btn>button:hover{opacity:0.6 !important;color:#fff !important}
    </style>""", unsafe_allow_html=True)

# ==========================================
# メイン
# ==========================================
st.set_page_config(page_title="提案力道場", layout="centered")
load_css()

if 'scene' not in st.session_state:
    st.session_state.update({
        'scene': 'title',
        'level': 1,
        'theme': None,
        'hints_unlocked': 0,
        # --- タイマー ---
        'prep_start': 0.0,      # 作戦会議タイマー開始時刻
        'prep_time': 0.0,       # 確定した作戦会議時間（秒）
        'pitch_start': 0.0,     # ピッチタイマー開始時刻
        'pitch_time': 0.0,      # 確定したピッチ時間（秒）
        'pitch_recording': False,  # 録音開始ボタンを押したか
        # -----------------
        'results': [],
        'transcript': '',
        'play_sound': None,
    })

# --- 効果音再生（ページ最上部で1回だけ） ---
if st.session_state.get('play_sound'):
    play_sound(st.session_state.play_sound)
    st.session_state.play_sound = None

# ==========================================
# タイトル
# ==========================================
if st.session_state.scene == 'title':
    st.markdown("# 🥋 提案力道場")
    st.markdown("### 〜師匠と磨く、30秒で心を動かす技〜")
    st.write("")
    st.write("汝は3人の強敵と対峙する運命にある...")
    st.write("Lv.1 👔 お客様の課長")
    st.write("Lv.2 🎩 お客様の部長")
    st.write("Lv.3 👑 お客様の経営層")
    st.markdown("""<div class="core-info-box">
    ⏱️ <strong>30秒ピッチの心得</strong><br>
    30秒で話せるのは約150〜175文字。施策は1〜2つに絞れ。<br>
    大事なのは「フック（掴み）→ 施策 → 着地（効果）」の流れじゃ。
    </div>""", unsafe_allow_html=True)
    st.write("")
    if st.button("⚔️ 修行を開始する"):
        st.session_state.scene = 'theme_select'
        st.session_state.play_sound = 'start'
        st.rerun()

# ==========================================
# テーマ選択
# ==========================================
elif st.session_state.scene == 'theme_select':
    lv = st.session_state.level
    boss = LEVELS[lv]
    play_sound("encounter")
    st.markdown(f"""<div class="dragon-quest-box">
    {boss['emoji']}<br><br>Lv.{lv}<br>{boss['name']}<br>が<br>あらわれた！
    </div>""", unsafe_allow_html=True)
    st.write(f"視点: **{boss['perspective']}**")
    st.write("### 🎲 試練を選べ")
    c1,c2,c3 = st.columns(3)
    for col, key, label in [
        (c1, "DX", "⚡ DX\n（デジタルの光）"),
        (c2, "コスト削減", "💰 コスト削減\n（黄金の節約）"),
        (c3, "納期遅延", "⏰ 納期遅延\n（運命の時計）"),
    ]:
        with col:
            if st.button(label):
                st.session_state.theme = key
                st.session_state.hints_unlocked = 0
                # ★ 作戦会議タイマー：テーマ選択と同時にスタート
                st.session_state.prep_start = time.time()
                st.session_state.prep_time = 0.0
                st.session_state.scene = 'quest'
                st.session_state.play_sound = 'select'
                st.rerun()

# ==========================================
# お題・作戦会議（タイマー自動スタート済み）
# ==========================================
elif st.session_state.scene == 'quest':
    lv = st.session_state.level
    th = st.session_state.theme
    boss = LEVELS[lv]
    ti = THEMES[th]

    st.markdown(f"## {boss['emoji']} Lv.{lv}: {boss['name']}")
    st.markdown(f"### {ti['title']}")

    # ★ カウントアップタイマー（JS）
    elapsed_init = int(time.time() - st.session_state.prep_start)
    timer_id = "prep_timer"
    st.markdown(f"""
    <div class="timer-label">⏱️ 作戦会議タイム（計測中）</div>
    <div id="{timer_id}" class="timer-box">{fmt_time(elapsed_init)}</div>
    <script>
    (function() {{
        var startEpoch = {st.session_state.prep_start};
        var el = document.getElementById('{timer_id}');
        if (!el) return;
        if (window._prepTimer) clearInterval(window._prepTimer);
        window._prepTimer = setInterval(function() {{
            var e = Math.floor(Date.now() / 1000 - startEpoch);
            var m = Math.floor(e / 60);
            var s = e % 60;
            el.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
        }}, 500);
    }})();
    </script>
    """, unsafe_allow_html=True)

    st.info(f"📋 **状況**\n\n{ti['situation'][lv]}")
    st.warning(f"🎯 **ミッション**\n\n{ti['mission'][lv]}")
    st.markdown(f"""<div class="core-info-box">🔑 <strong>核心情報（ピッチに使え）</strong>: {ti['core_info'][lv]}</div>""", unsafe_allow_html=True)

    st.write("### 💡 知恵の宝珠（ヒント）")
    for i in range(3):
        if i < st.session_state.hints_unlocked:
            st.success(ti['hints'][i])
        elif i == st.session_state.hints_unlocked:
            if st.button(f"🔓 ヒント{i+1}を見る", key=f"qh_{i}"):
                st.session_state.hints_unlocked += 1
                st.session_state.play_sound = 'hint'
                st.rerun()
        else:
            st.write(f"🔒 ヒント{i+1}（前のヒントを解放せよ）")

    st.write("")
    if st.button("🎤 いざ、本番へ（30秒ピッチ）"):
        # ★ 作戦会議タイマー停止・確定
        st.session_state.prep_time = time.time() - st.session_state.prep_start
        # ★ ピッチタイマーはまだ開始しない（録音開始ボタンを押すまで待つ）
        st.session_state.pitch_start = 0.0
        st.session_state.pitch_time = 0.0
        st.session_state.pitch_recording = False
        st.session_state.scene = 'pitch'
        st.session_state.play_sound = 'battle'
        st.rerun()

# ==========================================
# ピッチ（録音）
# ==========================================
elif st.session_state.scene == 'pitch':
    lv = st.session_state.level
    th = st.session_state.theme
    boss = LEVELS[lv]
    ti = THEMES[th]

    st.markdown(f"## {boss['emoji']} {boss['name']}へのピッチ")
    st.markdown(f"### {ti['title']}")
    st.info(f"📋 **状況**\n\n{ti['situation'][lv]}")
    st.warning(f"🎯 **ミッション**\n\n{ti['mission'][lv]}")
    st.markdown(f"""<div class="core-info-box">🔑 <strong>核心情報</strong>: {ti['core_info'][lv]}<br>
    ⏱️ <strong>30秒</strong>（約150〜175文字）で伝えよ！</div>""", unsafe_allow_html=True)

    st.write("")

    # ★ STEP1: 録音開始ボタンを押すまでの待機状態
    if not st.session_state.pitch_recording:
        st.markdown("""<div style="background:rgba(251,191,36,.1);border:2px dashed #fbbf24;
        border-radius:8px;padding:14px;text-align:center;font-size:15px;margin-bottom:12px;">
        🎙️ 準備ができたら下のボタンを押せ。<br>
        <strong>ボタンを押した瞬間からピッチタイムの計測が始まる。</strong>
        </div>""", unsafe_allow_html=True)
        if st.button("🎙️ 録音開始 ＆ タイマースタート"):
            # ★ このタイミングで pitch_start を記録
            st.session_state.pitch_start = time.time()
            st.session_state.pitch_recording = True
            st.rerun()

    # ★ STEP2: 録音開始ボタンを押した後 → タイマー表示 ＆ mic_recorder
    else:
        pitch_elapsed_init = int(time.time() - st.session_state.pitch_start)
        st.markdown(f"""
        <div class="timer-label">🎙️ ピッチタイム（計測中）</div>
        <div id="pitch_timer" class="timer-box">{fmt_time(pitch_elapsed_init)}</div>
        <script>
        (function() {{
            var startEpoch = {st.session_state.pitch_start};
            var el = document.getElementById('pitch_timer');
            if (!el) return;
            if (window._pitchTimer) clearInterval(window._pitchTimer);
            window._pitchTimer = setInterval(function() {{
                var e = Math.floor(Date.now() / 1000 - startEpoch);
                var m = Math.floor(e / 60);
                var s = e % 60;
                el.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                if (e >= 30) {{
                    el.style.color = '#ef4444';
                    el.style.borderColor = '#ef4444';
                }}
            }}, 500);
        }})();
        </script>
        """, unsafe_allow_html=True)

        st.markdown("""<div style="text-align:center;font-size:14px;color:#a3e635;margin-bottom:8px;">
        ↓ マイクボタンを押して話し始め、終わったら停止ボタンを押せ</div>""", unsafe_allow_html=True)

        audio = mic_recorder(
            start_prompt="🔴 マイクON（話し始めよ）",
            stop_prompt="⏹️ 停止（計測終了）",
            key='rec'
        )
        if audio:
            # ★ ピッチタイマー停止・確定（停止ボタンを押した瞬間）
            st.session_state.pitch_time = time.time() - st.session_state.pitch_start
            st.session_state.pitch_recording = False
            with st.spinner("🥋 師匠が評価中..."):
                text = transcribe_whisper(audio['bytes'])
                if len(text) < 5:
                    st.warning("声が聞こえぬぞ、弟子よ...")
                else:
                    st.session_state.transcript = text
                    result = evaluate_pitch(lv, th, text)
                    result['transcript'] = text
                    result['theme'] = th
                    result['prep_time'] = st.session_state.prep_time
                    result['pitch_time'] = st.session_state.pitch_time
                    st.session_state.results.append(result)
                    st.session_state.play_sound = f"result_{result.get('rank','C').lower()}"
                    st.session_state.scene = 'result'
                    st.rerun()

# ==========================================
# 評価結果
# ==========================================
elif st.session_state.scene == 'result':
    r = st.session_state.results[-1]
    st.markdown("## 🥋 師匠の評価")
    re_ = {"S":"🌟","A":"⭐","B":"✨","C":"💫"}
    sc = r.get('score', 50)
    st.markdown(f"# {re_.get(r['rank'],'✨')} ランク: {r['rank']} ({sc}点)")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🎯 フック", f"{r.get('hook_score',0)}点")
    c2.metric("🔧 施策", f"{r.get('measure_score',0)}点")
    c3.metric("📊 根拠", f"{r.get('evidence_score',0)}点")
    c4.metric("🏁 着地", f"{r.get('landing_score',0)}点")

    # ★ タイム記録の表示
    prep_t = r.get('prep_time', 0)
    pitch_t = r.get('pitch_time', 0)
    st.markdown(f"""<div class="time-record-box">
    ⏱️ <strong>タイム記録</strong><br>
    📝 作戦会議: <strong>{fmt_time(prep_t)}</strong>（{int(prep_t)}秒）　
    🎙️ ピッチ: <strong>{fmt_time(pitch_t)}</strong>（{int(pitch_t)}秒）
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="village-elder">
    <p><strong>🎤 汝の言葉:</strong></p><p>{r.get('transcript','')}</p><br>
    <p><strong>✅ 良かった点:</strong></p><p>{r.get('good_points','')}</p><br>
    <p><strong>💡 改善点:</strong></p><p>{r.get('improvements','')}</p><br>
    <p><strong>🎯 次回へのアドバイス:</strong></p><p>{r.get('next_tips','')}</p><br>
    <p><strong>💬 師匠の言葉:</strong></p><p>{r.get('comment','精進せよ！')}</p>
    </div>""", unsafe_allow_html=True)

    if st.session_state.level < 3:
        if st.button("➡️ 次の強敵へ"):
            st.session_state.level += 1
            st.session_state.scene = 'theme_select'
            st.session_state.play_sound = 'levelup'
            st.rerun()
    else:
        if st.button("👑 免許皆伝へ"):
            st.session_state.scene = 'ending'
            st.session_state.play_sound = 'ending'
            st.rerun()

# ==========================================
# 免許皆伝
# ==========================================
elif st.session_state.scene == 'ending':
    st.markdown("## 👑 修行の成果")
    scores = [r.get('score', 50) for r in st.session_state.results]
    avg = sum(scores) / len(scores) if scores else 0
    all_s = all(r.get('rank') == 'S' for r in st.session_state.results)

    if avg >= 90:
        title = "🌟 提案力の達人"
        cmt = "見事じゃ！汝の30秒ピッチは一流。お客様の心を30秒で掴む技を手に入れた。自信を持って実戦に挑め！"
    elif avg >= 70:
        title = "⭐ 熟練の提案者"
        cmt = "良き修行であった。フックの切れ味は十分。施策の具体性と着地の精度をさらに磨けば、必ず達人の域に至る！"
    elif avg >= 50:
        title = "✨ 修行中の弟子"
        cmt = "まずまずの成果じゃ。シチュエーションの固有名詞と数値をもっと使え。ヒント3の30秒テンプレートを活用して再挑戦せよ！"
    else:
        title = "💫 見習い弟子"
        cmt = "まだまだじゃな。されど諦めるな。まずは「お客様の名前と数値」を最初の一文に入れることから始めよ。千里の道も一歩からじゃ！"

    st.markdown(f"# {title}")
    st.markdown(f"### 総合スコア: {avg:.0f}点")
    st.markdown(f"""<div class="village-elder">
    <p><strong>💬 師匠の総評:</strong></p><p>{cmt}</p><br>
    <p><strong>📊 修行の記録</strong></p></div>""", unsafe_allow_html=True)

    for i, r in enumerate(st.session_state.results, 1):
        ln = LEVELS[i]['name']
        tn = r.get('theme', '')
        prep_t = r.get('prep_time', 0)
        pitch_t = r.get('pitch_time', 0)
        st.write(f"**Lv.{i} {ln}** - {tn} : ランク{r.get('rank','-')}（{r.get('score',0)}点）")
        st.write(f"　フック{r.get('hook_score',0)} / 施策{r.get('measure_score',0)} / 根拠{r.get('evidence_score',0)} / 着地{r.get('landing_score',0)}")
        st.write(f"　⏱️ 作戦会議 {fmt_time(prep_t)} ／ 🎙️ ピッチ {fmt_time(pitch_t)}")

    st.write("")
    col_main, col_secret = st.columns([6, 1])
    with col_main:
        if st.button("🔄 もう一度修行する"):
            st.session_state.update({
                'scene': 'title', 'level': 1, 'results': [],
                'hints_unlocked': 0, 'prep_start': 0.0, 'prep_time': 0.0,
                'pitch_start': 0.0, 'pitch_time': 0.0, 'play_sound': 'start'
            })
            st.rerun()

    # ★ 全レベルSランクで隠しボタン出現
    with col_secret:
        if all_s:
            st.markdown('<div class="secret-btn">', unsafe_allow_html=True)
            if st.button("★", key="secret_door"):
                st.session_state.scene = 'secret_ending'
                st.session_state.play_sound = 'secret'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 隠しエンディング（全Sランク達成者のみ）
# ==========================================
elif st.session_state.scene == 'secret_ending':
    st.markdown("""
    <style>
    .main { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%) !important; }
    .secret-title { font-family: 'Press Start 2P', cursive; font-size: 20px; color: #fbbf24;
      text-align: center; text-shadow: 0 0 20px #fbbf24, 0 0 40px #f59e0b; margin: 20px 0; line-height: 2; }
    .secret-msg { background: rgba(0,0,0,0.7); border: 2px solid #fbbf24;
      border-radius: 12px; padding: 24px; margin: 20px 0; font-size: 16px;
      line-height: 2; color: #fef3c7; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="secret-title">✨ 隠しエンディング ✨<br>〜 真の達人へ 〜</div>', unsafe_allow_html=True)

    # ★ 音楽ファイル（secret_ending_music.mp3 を同ディレクトリに配置）
    music_path = "secret_ending_music.mp3"
    if os.path.exists(music_path):
        with open(music_path, "rb") as f:
            st.audio(f.read(), format="audio/mp3", autoplay=True)
    else:
        st.info("🎵 BGMファイル（secret_ending_music.mp3）をアプリと同じフォルダに配置してください。")

    # ★ 画像ファイル（secret_ending_image.png / .jpg を同ディレクトリに配置）
    for img_name in ["secret_ending_image.png", "secret_ending_image.jpg", "secret_ending_image.jpeg"]:
        if os.path.exists(img_name):
            st.image(img_name, use_container_width=True)
            break
    else:
        st.info("🖼️ 画像ファイル（secret_ending_image.png）をアプリと同じフォルダに配置してください。")

    st.markdown("""<div class="secret-msg">
    全レベル S ランク達成。<br><br>
    汝はただの提案者ではない。<br>
    30秒で、人の心を動かす者だ。<br><br>
    師匠として誇りに思う。<br>
    これからも、言葉を磨き続けよ。
    </div>""", unsafe_allow_html=True)

    if st.button("🔙 結果に戻る"):
        st.session_state.scene = 'ending'
        st.rerun()
