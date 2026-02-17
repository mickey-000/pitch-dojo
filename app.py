# -*- coding: utf-8 -*-
import streamlit as st
from streamlit_mic_recorder import mic_recorder
from openai import OpenAI
from google import genai
import time, json, io

# ==========================================
# 提案力道場 v2 - 設定
# ==========================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
GENAI_API_KEY = st.secrets.get("GENAI_API_KEY", "YOUR_GEMINI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
genai_client = genai.Client(api_key=GENAI_API_KEY)

# ==========================================
# 効果音システム（Web Audio API）
# ==========================================
SOUND_SCRIPTS = {
    "start": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25, 659.25, 783.99, 1046.50];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'square';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.15, ac.currentTime + i*0.12);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.12 + 0.2);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.12);
                o.stop(ac.currentTime + i*0.12 + 0.2);
            });
        } catch(e){}
    })();
    </script>
    """,
    "encounter": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [220, 277.18, 329.63, 220, 277.18, 329.63, 440];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'square';
                o.frequency.value = freq;
                const t = i < 3 ? i*0.08 : 0.3 + (i-3)*0.08;
                g.gain.setValueAtTime(0.12, ac.currentTime + t);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + t + 0.15);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + t);
                o.stop(ac.currentTime + t + 0.15);
            });
        } catch(e){}
    })();
    </script>
    """,
    "select": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const o = ac.createOscillator();
            const g = ac.createGain();
            o.type = 'square';
            o.frequency.setValueAtTime(880, ac.currentTime);
            o.frequency.setValueAtTime(1108, ac.currentTime + 0.06);
            g.gain.setValueAtTime(0.12, ac.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.15);
            o.connect(g); g.connect(ac.destination);
            o.start(); o.stop(ac.currentTime + 0.15);
        } catch(e){}
    })();
    </script>
    """,
    "hint": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [587.33, 783.99, 987.77];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'triangle';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.15, ac.currentTime + i*0.1);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.1 + 0.25);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.1);
                o.stop(ac.currentTime + i*0.1 + 0.25);
            });
        } catch(e){}
    })();
    </script>
    """,
    "battle": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [440, 554.37, 659.25, 880];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'sawtooth';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.08, ac.currentTime + i*0.1);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.1 + 0.2);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.1);
                o.stop(ac.currentTime + i*0.1 + 0.2);
            });
        } catch(e){}
    })();
    </script>
    """,
    "result_s": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25,523.25,0,523.25,0,415.30,523.25,0,659.25,0,0,329.63];
            notes.forEach((freq, i) => {
                if(freq === 0) return;
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'square';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.12, ac.currentTime + i*0.09);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.09 + 0.15);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.09);
                o.stop(ac.currentTime + i*0.09 + 0.15);
            });
        } catch(e){}
    })();
    </script>
    """,
    "result_a": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25, 659.25, 783.99];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'square';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.12, ac.currentTime + i*0.15);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.15 + 0.3);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.15);
                o.stop(ac.currentTime + i*0.15 + 0.3);
            });
        } catch(e){}
    })();
    </script>
    """,
    "result_b": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [392, 440];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'triangle';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.12, ac.currentTime + i*0.2);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.2 + 0.3);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.2);
                o.stop(ac.currentTime + i*0.2 + 0.3);
            });
        } catch(e){}
    })();
    </script>
    """,
    "result_c": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [311.13, 261.63];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'triangle';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.12, ac.currentTime + i*0.25);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.25 + 0.4);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.25);
                o.stop(ac.currentTime + i*0.25 + 0.4);
            });
        } catch(e){}
    })();
    </script>
    """,
    "levelup": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25,587.33,659.25,698.46,783.99,880,987.77,1046.50];
            notes.forEach((freq, i) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'square';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.1, ac.currentTime + i*0.08);
                g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + i*0.08 + 0.2);
                o.connect(g); g.connect(ac.destination);
                o.start(ac.currentTime + i*0.08);
                o.stop(ac.currentTime + i*0.08 + 0.2);
            });
        } catch(e){}
    })();
    </script>
    """,
    "ending": """
    <script>
    (function(){
        try {
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const melody = [
                [523.25,0.2],[659.25,0.2],[783.99,0.2],[1046.50,0.4],
                [783.99,0.15],[880,0.15],[1046.50,0.5]
            ];
            let t = ac.currentTime;
            melody.forEach(([freq, dur]) => {
                const o = ac.createOscillator();
                const g = ac.createGain();
                o.type = 'square';
                o.frequency.value = freq;
                g.gain.setValueAtTime(0.1, t);
                g.gain.exponentialRampToValueAtTime(0.001, t + dur);
                o.connect(g); g.connect(ac.destination);
                o.start(t); o.stop(t + dur);
                t += dur * 0.8;
            });
        } catch(e){}
    })();
    </script>
    """
}

def play_sound(sound_name):
    """効果音を再生する"""
    if sound_name in SOUND_SCRIPTS:
        st.markdown(SOUND_SCRIPTS[sound_name], unsafe_allow_html=True)

# ==========================================
# ゲーム設定
# ==========================================
LEVELS = {
    1: {
        "name": "お客様の課長",
        "emoji": "👔",
        "time": 120,
        "perspective": "現場",
    },
    2: {
        "name": "お客様の部長",
        "emoji": "🎩",
        "time": 120,
        "perspective": "部門",
    },
    3: {
        "name": "お客様の経営層",
        "emoji": "👑",
        "time": 60,
        "perspective": "全社",
    }
}

THEMES = {
    "DX": {
        "title": "⚡ DX（デジタルの光）",
        "situation": {
            1: "製造部の検査工程で、検査員の田中さんが紙の検査記録シートに手書きで記入し、終業後にExcelへ転記している。1日あたり約1.5時間を転記作業に費やしており、先月は転記ミスが3件発生、うち1件は出荷後に顧客クレームに発展した。課長は「田中さんの本来の業務時間が削られている上に、データの信頼性も担保できない」と頭を抱えている。",
            2: "営業部と生産管理部がメールとExcelで受注情報をやり取りしており、先月は仕様変更の伝達漏れにより30台を誤生産、手戻りコスト150万円が発生した。部長は「受注から生産までの情報が一元化されていないのが根本原因だ」と問題視している。",
            3: "競合のS社が受注から生産計画まで一気通貫でデジタル化し、見積回答を即日化。当社は平均5営業日かかっており、今期の相見積もりでS社に負けた案件が前年比8件増加、失注額は推定4,000万円。営業本部からは「スピードで負けている」と報告が相次いでいる。"
        },
        "mission": {
            1: "👔 検査工程の転記問題を解決する打ち手を、30秒でお客様の課長に提案せよ。",
            2: "🎩 受注から生産までの情報連携を改善する方法を、30秒でお客様の部長に提案せよ。",
            3: "👑 見積回答スピードで競合に勝つ戦略を、30秒でお客様の経営層に提案せよ。"
        },
        "core_info": {
            1: "田中さん / 1.5時間/日 / ミス3件 / 顧客クレーム1件",
            2: "30台誤生産 / 150万円 / メールとExcel / 情報の一元化",
            3: "S社 / 即日 vs 5営業日 / 8件増 / 4,000万円"
        },
        "hints": [
            "【第1のヒント：フックの極意】\n最初の一文で相手の痛みを掴め。「課長、田中さんの転記作業の件ですが」と切り出すだけで、相手は「わかってくれている」と感じる。シチュエーションの固有名詞（人名・数値）を最初の一文に入れよう。",
            "【第2のヒント：施策の磨き方】\n「デジタル化」「見える化」はバズワード。師匠は認めぬ。\n具体的なツール名・仕組み名を使え：\n・悪い例：「デジタル化します」\n・良い例：「タブレット端末での直接入力に切り替えます」\n1〜2つの施策を深く語る方が、浅い3つより刺さる。",
            "【第3のヒント：30秒テンプレート】\n「【フック】○○課長、（固有名詞＋数値）の件ですが、（相手の痛み）かと存じます。\n【施策】ご提案は、（具体的な施策名）の導入です。（補足1文）\n【着地】これにより（定量効果）を実現し、（状態変化）いたします。」\n\n例）課長向け：\n「課長、田中さんが毎日1.5時間かけている転記作業の件ですが、先月のミス3件は深刻です。ご提案はタブレット端末での現場直接入力です。規格外の値には自動アラートも設定します。転記作業ゼロ、ミスによるクレームを根絶します。」"
        ]
    },
    "コスト削減": {
        "title": "💰 コスト削減（黄金の節約）",
        "situation": {
            1: "製造ラインの段取り替えに毎回45分かかり、年間で約800時間の稼働ロスが発生している。ベテランの鈴木さんだけが速く段取りできるが、マニュアルがないため他のメンバーでは時間が1.5倍かかる。課長は「鈴木さんが休むとラインが回らない」と不安を感じている。",
            2: "主要部品のサプライヤー5社に対し、担当者ごとにバラバラの価格交渉をしており、同じ部品でも単価が最大15%異なっている。年間調達額3億円のうち、集約・統一により年間2,000万円の削減余地があるが、改革が進んでいない。",
            3: "売上総利益率が28%と業界平均の35%を7ポイント下回っており、中期経営計画の目標33%に対して初年度の改善はわずか0.5ポイント。主因は設備稼働率の低さと外注加工費の高止まりにある。経営会議では「構造的にコスト体質を変えなければ成長投資の原資が確保できない」と議論されている。"
        },
        "mission": {
            1: "👔 段取り替えのロスを削減する打ち手を、30秒でお客様の課長に提案せよ。",
            2: "🎩 調達コストの構造的な削減方法を、30秒でお客様の部長に提案せよ。",
            3: "👑 利益率を改善する構造改革の方向性を、30秒でお客様の経営層に提案せよ。"
        },
        "core_info": {
            1: "45分/回 / 800時間/年 / 鈴木さん / 1.5倍",
            2: "5社 / 単価差15% / 3億円 / 2,000万円削減余地",
            3: "28% vs 35% / 目標33% / 初年度+0.5pt / 成長投資の原資"
        },
        "hints": [
            "【第1のヒント：フックの極意】\n「コスト削減しましょう」では相手の心は動かない。\n相手が今まさに感じている痛みを、固有名詞と数値で言語化せよ。\n・課長なら：「鈴木さんが休むとラインが止まる不安」\n・部長なら：「同じ部品で15%も単価が違う理不尽さ」\n・経営層なら：「業界平均から7ポイント離された焦り」",
            "【第2のヒント：施策の磨き方】\n30秒で語れる施策は1〜2つが限界。最も効果の大きい打ち手を選べ。\n・悪い例：「効率化します」「最適化を図ります」\n・良い例：「鈴木さんの段取り手順を動画撮影してビジュアルマニュアルを作成します」\n聞いた相手が「来週から始められそうだ」と思える具体度を目指せ。",
            "【第3のヒント：30秒テンプレート】\n「【フック】○○部長、（固有名詞＋数値）の件ですが、（相手の痛み）かと存じます。\n【施策】ご提案は（具体的な施策名）です。（補足1文）\n【着地】これにより（定量効果）を実現いたします。」\n\n例）部長向け：\n「部長、5社のサプライヤーで同じ部品の単価が最大15%違っているのは、年間3億円の調達に対して大きなロスです。品目ごとの単価比較データベースを構築し、スコアカード制で評価を一本化します。初年度で1,500万円の削減を実現いたします。」"
        ]
    },
    "納期遅延": {
        "title": "⏰ 納期遅延（運命の時計）",
        "situation": {
            1: "先月、主要顧客のA社（年間取引額5,000万円）への納品が10日遅延した。原因は生産管理担当の佐藤さんがインフルエンザで1週間不在となり、部品の発注タイミングを逃したこと。佐藤さん以外に発注業務を担えるメンバーがいなかった。A社からは「佐藤さんがいないと回らないのか。次回は取引見直し」と警告されている。",
            2: "今四半期で納期遅延が4件発生した。いずれも調達部の入荷遅れが製造部・品質管理部に波及する同じパターン。原因は部門ごとの管理方法がバラバラ（Excel・ホワイトボード・紙台帳）で、遅延情報がリアルタイムに共有されないこと。部長は「個々の部門は頑張っているが、つなぎ目で毎回遅れる」と認識している。",
            3: "納期遵守率が91%にとどまり、競合H社の98%に大きく劣後している。その結果、主要顧客のF社（年間1.2億円）から「遵守率95%以上が次回契約の条件」と通告され、G社（年間1.5億円）は既にH社への切り替えを始めている。合計2.7億円の売上を守るために、今期中の遵守率改善が急務。"
        },
        "mission": {
            1: "👔 属人化による納期遅延を防ぐ仕組みを、30秒でお客様の課長に提案せよ。",
            2: "🎩 部門間の遅延連鎖を止める方法を、30秒でお客様の部長に提案せよ。",
            3: "👑 顧客の信頼を回復し契約を守る戦略を、30秒でお客様の経営層に提案せよ。"
        },
        "core_info": {
            1: "A社 / 5,000万円 / 10日遅延 / 佐藤さん / 取引見直し",
            2: "4件 / 同じパターン / Excel・ホワイトボード・紙台帳 / つなぎ目",
            3: "91% vs H社98% / F社1.2億 / G社1.5億 / 2.7億円リスク / 95%条件"
        },
        "hints": [
            "【第1のヒント：フックの極意】\nお客様が最も恐れていることを、最初の一文で言い当てよ。\n・課長：「A社様の5,000万円のお取引を失うこと」\n・部長：「また同じパターンで遅延が起きること」\n・経営層：「F社様・G社様の合計2.7億円が流出すること」\n恐れを言語化された相手は「この人はわかっている」と信頼する。",
            "【第2のヒント：施策の磨き方】\nお客様への提案では、「御社は〜すべき」より「弊社がご提案するのは〜です」が刺さる。\n・悪い例：「属人化を解消してください」\n・良い例：「佐藤さんの発注業務を工程分解したデジタルマニュアルの作成をご提案します」\n施策はお客様が「それならやってみたい」と思える具体度を目指せ。",
            "【第3のヒント：30秒テンプレート】\n「【フック】○○課長、（固有名詞＋数値）の件ですが、（相手の痛み）かと存じます。\n【施策】弊社からのご提案は（具体的な施策名）です。（補足1文）\n【着地】これにより（定量効果）を実現し、（状態変化）いたします。」\n\n例）課長向け：\n「課長、A社様への10日遅延の件ですが、5,000万円のお取引先から『次は見直し』と言われている以上、急務です。佐藤さんの発注業務のデジタルマニュアル作成と、副担当をつけるペア制をご提案します。佐藤さんが不在でも発注が止まらない体制を実現します。」"
        ]
    }
}

# ==========================================
# 音声認識（Whisper）
# ==========================================
def transcribe_whisper(audio_bytes):
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ja",
            response_format="text"
        )
        return transcript
    except Exception as e:
        st.error(f"音声認識エラー: {e}")
        return ""

# ==========================================
# 師匠の評価（Gemini）- v2 30秒ピッチ対応版
# ==========================================
def evaluate_pitch(level, theme, transcript):
    level_info = LEVELS[level]
    theme_info = THEMES[theme]

    prompt = f"""あなたは提案力道場の師匠です。30秒のエレベータピッチ（150〜175文字程度）を以下の基準で評価してください。

【評価対象】
相手: {level_info["name"]}（{level_info["perspective"]}視点）
テーマ: {theme}
シチュエーション: {theme_info['situation'][level]}
核心情報: {theme_info['core_info'][level]}
弟子の発言: {transcript}

【重要な前提】
- これは「お客様」への提案である。弟子は外部の提案者（営業・コンサルタント等）の立場。
- 30秒ピッチなので、施策は1〜2つで十分。3つ以上を求めない。
- 「御社」「ご提案」など、お客様への敬意ある表現が望ましい。

【評価4要素（各25点、合計100点）】

■ フック・課題把握（25点）
「お客様の痛みを自分の言葉で掴んでいるか」
25点: お客様の立場に立った課題の言い換え＋固有名詞・数値で具体化
20点: 固有名詞を使って課題に言及しているが、お客様目線がやや弱い
15点: 課題の方向性は合っているが、固有名詞・数値がない
10点: 一般的な課題認識にとどまる
5点: 課題の特定が曖昧
0点: フックなし（いきなり施策、または提案の体をなしていない）

■ 施策の具体性（25点）
「何をするかが具体的に伝わるか」
25点: ツール名・仕組み名が具体的で導入イメージが湧く（1〜2施策）
20点: 施策の方向性が具体的だがツール名・実装方法まで示されていない
15点: やりたいことは伝わるが手段が不明確
10点: バズワード寄り（「見える化」「効率化」「DX推進」等）
5点: 一般論（「改善する」「対策を打つ」）
0点: 施策への言及なし

■ 根拠・数値の活用（25点）
「シチュエーションの事実を使って説得力を出しているか」
25点: 固有名詞・数値を2つ以上、提案の根拠として自然に織り込んでいる
20点: 固有名詞・数値を1〜2つ使用しているが、提案との結びつきがやや弱い
15点: シチュエーションの状況には触れているが固有名詞・数値がない
10点: シチュエーションへの言及が一般的
5点: ほぼシチュエーションに触れていない
0点: 完全に一般論

■ 着地・効果（25点）
「結果どうなるかが伝わるか」
25点: 定量的効果＋具体的な状態変化が明示されている
20点: 定量的効果 or 具体的な状態変化のどちらかが示されている
15点: 効果の方向性はあるが数値も状態変化も曖昧
10点: 漠然と効果に触れている（「良くなるはず」）
5点: 効果がほぼ不明
0点: 効果への言及なし

【ランク判定】
S (90-100): 全要素が◎〜○。「この30秒で次の会議に繋がる」レベル
A (70-89): 3要素以上が○以上。「方向性は良い、もう少し詰めて」レベル
B (50-69): 課題把握はできており施策の方向性もある。「言いたいことはわかるが具体的に」レベル
C (0-49): 課題把握が曖昧 or 施策が一般論。「何が言いたいのかわからない」レベル

【BとCの判定基準（重要・厳守）】
Bの人: シチュエーションの状況に触れている。施策を1つは方向性レベルで示せている。効果にも言及しているが漠然。
Cの人: シチュエーションに触れていない。バズワード止まり。効果が「思います」「はず」レベル。

【フィードバックの書き方】

良かった点:
- 発言から具体的に引用して褒める
- お客様への話し方として良かった点にも触れる

改善点:
- 「〜が足りない」ではなく「〜を加えるとさらに良くなる」と表現
- 30秒で使える具体的なフレーズを例示する

次回アドバイス:
- シチュエーションから使うべき固有名詞・数値を2つ以上明示
- 「こう言い換えると刺さる」という具体例を示す
- お客様への提案として適切な表現例を示す

師匠の言葉:
- ポジティブで励ます内容（50文字程度）

以下のJSON形式で返してください：
{{
  "score": 合計点数（0-100の整数）,
  "rank": "S/A/B/C",
  "hook_score": フックの点数（0/5/10/15/20/25の6段階のみ）,
  "measure_score": 施策の点数（0/5/10/15/20/25の6段階のみ）,
  "evidence_score": 根拠の点数（0/5/10/15/20/25の6段階のみ）,
  "landing_score": 着地の点数（0/5/10/15/20/25の6段階のみ）,
  "good_points": "発言から引用して良かった点を具体的に（100文字程度）",
  "improvements": "30秒で使えるフレーズを例示して改善提案（100文字程度）",
  "next_tips": "次回使うべき固有名詞・数値・言い換え例を明示（100文字程度）",
  "comment": "師匠の温かい励まし（50文字程度）"
}}"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = genai_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean_json)
            if 'score' not in result:
                result['score'] = 50
            if 'rank' not in result:
                result['rank'] = 'B'
            return result
        except Exception as e:
            if '429' in str(e) and attempt < max_retries - 1:
                time.sleep(10)
                continue
            return {
                "score": 0,
                "rank": "C",
                "hook_score": 0,
                "measure_score": 0,
                "evidence_score": 0,
                "landing_score": 0,
                "good_points": "システムエラーが発生した。",
                "improvements": "もう一度挑戦せよ。",
                "next_tips": "再度試してみよ。",
                "comment": f"エラー: {e}"
            }

# ==========================================
# CSSスタイル（道場風）
# ==========================================
def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

    .main {
        background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
        color: #fff;
    }

    .main, .stApp {
        transition: none !important;
    }

    .stButton>button {
        background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 100%);
        color: #000;
        border: 3px solid #fff;
        font-weight: bold;
        font-size: 18px;
        padding: 12px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        min-height: 80px;
        white-space: normal;
    }
    .stButton>button:hover {
        background: linear-gradient(180deg, #fcd34d 0%, #fbbf24 100%);
        transform: translateY(-2px);
    }
    h1, h2, h3 {
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    .village-elder {
        background: rgba(0,0,0,0.6);
        border: 3px solid #fbbf24;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
    .countdown {
        font-size: 48px;
        font-weight: bold;
        color: #fbbf24;
        text-align: center;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.8);
    }

    .dragon-quest-box {
        background: #000;
        border: 4px solid #fff;
        border-radius: 0px;
        padding: 30px 40px;
        margin: 20px 0;
        font-family: 'Press Start 2P', cursive;
        font-size: 24px;
        color: #fff;
        text-shadow: 3px 3px 0px #000;
        line-height: 2.2;
        box-shadow: 0 8px 16px rgba(0,0,0,0.8);
        text-align: center;
        word-break: keep-all;
    }

    .core-info-box {
        background: rgba(251,191,36,0.15);
        border: 2px solid #fbbf24;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 10px 0;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# メインゲーム
# ==========================================
st.set_page_config(page_title="提案力道場", layout="centered")
load_custom_css()

if 'scene' not in st.session_state:
    st.session_state.update({
        'scene': 'title',
        'level': 1,
        'theme': None,
        'hints_unlocked': 0,
        'prep_start': 0,
        'results': [],
        'transcript': '',
        'play_sound': None
    })

# 効果音の再生（シーン遷移時）
if st.session_state.get('play_sound'):
    play_sound(st.session_state.play_sound)
    st.session_state.play_sound = None

# ==========================================
# タイトル画面
# ==========================================
if st.session_state.scene == 'title':
    st.markdown("# 🥋 提案力道場")
    st.markdown("### 〜師匠と磨く、30秒で心を動かす技〜")
    st.write("")
    st.write("汝は3人の強敵と対峙する運命にある...")
    st.write("Lv.1 👔 お客様の課長")
    st.write("Lv.2 🎩 お客様の部長")
    st.write("Lv.3 👑 お客様の経営層")
    st.write("")
    st.markdown("""
    <div class="core-info-box">
    ⏱️ <strong>30秒ピッチの心得</strong><br>
    30秒で話せるのは約150〜175文字。施策は1〜2つに絞れ。<br>
    大事なのは「フック（掴み）→ 施策 → 着地（効果）」の流れじゃ。
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    if st.button("⚔️ 修行を開始する"):
        st.session_state.scene = 'theme_select'
        st.session_state.play_sound = 'start'
        st.rerun()

# ==========================================
# テーマ選択
# ==========================================
elif st.session_state.scene == 'theme_select':
    level = st.session_state.level
    boss = LEVELS[level]

    play_sound("encounter")

    st.markdown(f"""
    <div class="dragon-quest-box">
        {boss['emoji']}<br>
        <br>
        Lv.{level}<br>
        {boss['name']}<br>
        が<br>
        あらわれた！
    </div>
    """, unsafe_allow_html=True)

    st.write(f"視点: **{boss['perspective']}**")
    st.write("")
    st.write("### 🎲 試練を選べ")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⚡ DX\n（デジタルの光）"):
            st.session_state.theme = "DX"
            st.session_state.hints_unlocked = 0
            st.session_state.scene = 'quest'
            st.session_state.play_sound = 'select'
            st.rerun()

    with col2:
        if st.button("💰 コスト削減\n（黄金の節約）"):
            st.session_state.theme = "コスト削減"
            st.session_state.hints_unlocked = 0
            st.session_state.scene = 'quest'
            st.session_state.play_sound = 'select'
            st.rerun()

    with col3:
        if st.button("⏰ 納期遅延\n（運命の時計）"):
            st.session_state.theme = "納期遅延"
            st.session_state.hints_unlocked = 0
            st.session_state.scene = 'quest'
            st.session_state.play_sound = 'select'
            st.rerun()

# ==========================================
# お題表示とヒント
# ==========================================
elif st.session_state.scene == 'quest':
    level = st.session_state.level
    theme = st.session_state.theme
    boss = LEVELS[level]
    theme_info = THEMES[theme]

    st.markdown(f"## {boss['emoji']} Lv.{level}: {boss['name']}")
    st.markdown(f"### {theme_info['title']}")

    st.info(f"📋 **状況**\n\n{theme_info['situation'][level]}")
    st.warning(f"🎯 **ミッション**\n\n{theme_info['mission'][level]}")

    st.markdown(f"""
    <div class="core-info-box">
    🔑 <strong>核心情報（ピッチに使え）</strong>: {theme_info['core_info'][level]}
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.write("### 💡 知恵の宝珠（ヒント）")

    for i in range(3):
        if i < st.session_state.hints_unlocked:
            st.success(theme_info['hints'][i])
        elif i == st.session_state.hints_unlocked:
            if st.button(f"🔓 ヒント{i+1}を見る", key=f"quest_hint_{i}"):
                st.session_state.hints_unlocked += 1
                st.session_state.play_sound = 'hint'
                st.rerun()
        else:
            st.write(f"🔒 ヒント{i+1}（前のヒントを解放せよ）")

    st.write("")
    if st.button("⚔️ 準備完了！作戦会議へ"):
        st.session_state.prep_start = 0
        st.session_state.scene = 'prep'
        st.session_state.play_sound = 'select'
        st.rerun()

# ==========================================
# 作戦会議（カウントダウン）
# ==========================================
elif st.session_state.scene == 'prep':
    level = st.session_state.level
    theme = st.session_state.theme
    boss = LEVELS[level]
    theme_info = THEMES[theme]

    if st.session_state.prep_start == 0:
        st.session_state.prep_start = time.time()

    elapsed = time.time() - st.session_state.prep_start
    remaining = max(0, int(boss['time'] - elapsed))

    st.markdown("## ⏱️ 作戦会議中...")
    st.markdown("*30秒で何を伝えるか、構成を練れ！*")

    countdown_id = f"cd_{int(st.session_state.prep_start)}"

    if remaining > 0:
        st.markdown(f"""
        <div id="{countdown_id}" class="countdown">{remaining // 60:02d}:{remaining % 60:02d}</div>
        <script>
        (function() {{
            let timeLeft = {remaining};
            const el = document.getElementById('{countdown_id}');
            if (!el) return;
            if (window._cdTimer) clearInterval(window._cdTimer);
            window._cdTimer = setInterval(() => {{
                if (timeLeft <= 0) {{
                    clearInterval(window._cdTimer);
                    el.style.color = '#ef4444';
                    el.textContent = '00:00';
                }} else {{
                    const m = Math.floor(timeLeft / 60);
                    const s = timeLeft % 60;
                    el.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                    timeLeft--;
                }}
            }}, 1000);
        }})();
        </script>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="countdown" style="color: #ef4444;">00:00</div>', unsafe_allow_html=True)
        st.success("作戦会議終了！いざ、本番へ！")

    st.write("")

    st.info(f"📋 **状況**\n\n{theme_info['situation'][level]}")
    st.warning(f"🎯 **ミッション**\n\n{theme_info['mission'][level]}")

    st.markdown(f"""
    <div class="core-info-box">
    🔑 <strong>核心情報（ピッチに使え）</strong>: {theme_info['core_info'][level]}
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.write("### 💡 知恵の宝珠（ヒント）")

    for i in range(3):
        if i < st.session_state.hints_unlocked:
            st.success(theme_info['hints'][i])
        elif i == st.session_state.hints_unlocked:
            if st.button(f"🔓 ヒント{i+1}を見る", key=f"prep_hint_{i}"):
                st.session_state.hints_unlocked += 1
                st.session_state.play_sound = 'hint'
                st.rerun()
        else:
            st.write(f"🔒 ヒント{i+1}（前のヒントを解放せよ）")

    st.write("")

    if st.button("🎤 いざ、本番へ（30秒ピッチ）"):
        st.session_state.prep_start = 0
        st.session_state.scene = 'pitch'
        st.session_state.play_sound = 'battle'
        st.rerun()

# ==========================================
# ピッチ実行
# ==========================================
elif st.session_state.scene == 'pitch':
    level = st.session_state.level
    theme = st.session_state.theme
    boss = LEVELS[level]
    theme_info = THEMES[theme]

    st.markdown(f"## {boss['emoji']} {boss['name']}へのピッチ")
    st.markdown(f"### {theme_info['title']}")
    st.info(f"📋 **状況**\n\n{theme_info['situation'][level]}")
    st.warning(f"🎯 **ミッション**\n\n{theme_info['mission'][level]}")

    st.markdown(f"""
    <div class="core-info-box">
    🔑 <strong>核心情報</strong>: {theme_info['core_info'][level]}<br>
    ⏱️ <strong>30秒</strong>（約150〜175文字）で伝えよ！
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    audio = mic_recorder(start_prompt="🎙️ 録音開始（30秒ピッチ）", stop_prompt="⏹️ 完了", key='rec')

    if audio:
        with st.spinner("🥋 師匠が評価中..."):
            text = transcribe_whisper(audio['bytes'])
            if len(text) < 5:
                st.warning("声が聞こえぬぞ、弟子よ...")
            else:
                st.session_state.transcript = text
                result = evaluate_pitch(level, theme, text)
                result['transcript'] = text
                result['theme'] = theme
                st.session_state.results.append(result)
                # ランクに応じた効果音を設定
                rank = result.get('rank', 'C')
                st.session_state.play_sound = f'result_{rank.lower()}'
                st.session_state.scene = 'result'
                st.rerun()

# ==========================================
# 師匠の評価
# ==========================================
elif st.session_state.scene == 'result':
    result = st.session_state.results[-1]

    st.markdown("## 🥋 師匠の評価")

    rank_emoji = {"S": "🌟", "A": "⭐", "B": "✨", "C": "💫"}
    score = result.get('score', 50)
    st.markdown(f"# {rank_emoji.get(result['rank'], '✨')} ランク: {result['rank']} ({score}点)")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 フック", f"{result.get('hook_score', 0)}点")
    with col2:
        st.metric("🔧 施策", f"{result.get('measure_score', 0)}点")
    with col3:
        st.metric("📊 根拠", f"{result.get('evidence_score', 0)}点")
    with col4:
        st.metric("🏁 着地", f"{result.get('landing_score', 0)}点")

    st.markdown(f"""
    <div class="village-elder">
        <p><strong>🎤 汝の言葉:</strong></p>
        <p>{result.get('transcript', '')}</p>
        <br>
        <p><strong>✅ 良かった点:</strong></p>
        <p>{result.get('good_points', '基本的な構造は見えておる。')}</p>
        <br>
        <p><strong>💡 改善点:</strong></p>
        <p>{result.get('improvements', 'さらなる具体性を目指そう。')}</p>
        <br>
        <p><strong>🎯 次回へのアドバイス:</strong></p>
        <p>{result.get('next_tips', '繰り返し稽古あるのみ！')}</p>
        <br>
        <p><strong>💬 師匠の言葉:</strong></p>
        <p>{result.get('comment', '精進せよ！')}</p>
    </div>
    """, unsafe_allow_html=True)

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
    avg_score = sum(scores) / len(scores) if scores else 0

    if avg_score >= 90:
        title = "🌟 提案力の達人"
        comment = "見事じゃ！汝の30秒ピッチは一流。お客様の心を30秒で掴む技を手に入れた。自信を持って実戦に挑め！"
    elif avg_score >= 70:
        title = "⭐ 熟練の提案者"
        comment = "良き修行であった。フックの切れ味は十分。施策の具体性と着地の精度をさらに磨けば、必ず達人の域に至る！"
    elif avg_score >= 50:
        title = "✨ 修行中の弟子"
        comment = "まずまずの成果じゃ。シチュエーションの固有名詞と数値をもっと使え。ヒント3の30秒テンプレートを活用して再挑戦せよ！"
    else:
        title = "💫 見習い弟子"
        comment = "まだまだじゃな。されど諦めるな。まずは「お客様の名前と数値」を最初の一文に入れることから始めよ。千里の道も一歩からじゃ！"

    st.markdown(f"# {title}")
    st.markdown(f"### 総合スコア: {avg_score:.0f}点")

    st.markdown(f"""
    <div class="village-elder">
        <p><strong>💬 師匠の総評:</strong></p>
        <p>{comment}</p>
        <br>
        <p><strong>📊 修行の記録</strong></p>
    </div>
    """, unsafe_allow_html=True)

    for i, r in enumerate(st.session_state.results, 1):
        level_name = LEVELS[i]['name']
        theme_name = r.get('theme', '')
        st.write(f"**Lv.{i} {level_name}** - {theme_name} : ランク{r.get('rank', '-')}（{r.get('score', 0)}点）")
        st.write(f"　フック{r.get('hook_score', 0)} / 施策{r.get('measure_score', 0)} / 根拠{r.get('evidence_score', 0)} / 着地{r.get('landing_score', 0)}")

    st.write("")
    if st.button("🔄 もう一度修行する"):
        st.session_state.scene = 'title'
        st.session_state.level = 1
        st.session_state.results = []
        st.session_state.hints_unlocked = 0
        st.session_state.prep_start = 0
        st.session_state.play_sound = 'start'
        st.rerun()
