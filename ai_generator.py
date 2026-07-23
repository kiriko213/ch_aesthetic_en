import os
import json
import random
import google.generativeai as genai
import datetime
import re

HOOK_PATTERNS = [
    {
        "type": "REALITY_SHATTERING",
        "instruction": "Start with a short, reality-shattering claim that instantly stops scrolling. Example: 'Stop believing this place is CGI.' or 'This isn't another planet, it's Earth.'"
    },
    {
        "type": "FORBIDDEN_SECRET",
        "instruction": "Start with a mysterious, forbidden secret hook. Example: 'The one place governments don't want you to see.' or 'Nobody is allowed to step foot here.'"
    },
    {
        "type": "WARNING_SURPASS",
        "instruction": "Start with a high-urgency or thrilling warning hook. Example: 'Step here and you won't survive 5 minutes.' or 'Do NOT visit this place alone.'"
    },
    {
        "type": "INTERACTIVE_CHALLENGE",
        "instruction": "Start with a high-impact country guessing challenge. Example: 'Can you guess this impossible country in 3 seconds?' or 'Only 1% of viewers know this spot.'"
    },
    {
        "type": "IMMERSIVE_CURIOSITY",
        "instruction": "Start with an immersive, hypothetical question. Example: 'What happens if you fall into this glowing hole?' or 'Imagine waking up in this hidden world.'"
    }
]

_cached_selected_model = None

def get_available_gemini_models():
    """Retrieve list of available models supporting generateContent."""
    try:
        models = list(genai.list_models())
        available = []
        for m in models:
            methods = getattr(m, 'supported_generation_methods', [])
            if 'generateContent' in methods:
                name = getattr(m, 'name', str(m)).replace('models/', '')
                available.append(name)
        return available
    except Exception as e:
        print(f"[Gemini Discovery] Warning: Failed to list models via API: {e}")
        return []

def extract_version_tuple(model_name):
    """Extracts version numbers as tuple for sorting, e.g. 'gemini-2.5-flash' -> (2, 5)."""
    matches = re.findall(r'\d+(?:\.\d+)?', model_name)
    if matches:
        try:
            parts = matches[0].split('.')
            return tuple(int(p) for p in parts)
        except ValueError:
            pass
    return ()

def select_best_model(available_models, exclude_models=None):
    """Select model by priority: GEMINI_MODEL -> Latest stable Flash -> Latest stable Flash Lite -> Any stable generateContent model."""
    if exclude_models is None:
        exclude_models = set()

    env_model = os.environ.get("GEMINI_MODEL")
    if env_model:
        clean_env = env_model.replace('models/', '')
        if clean_env not in exclude_models and (not available_models or clean_env in available_models):
            return clean_env

    candidates = [m for m in available_models if m not in exclude_models]

    stable_candidates = [m for m in candidates if not any(x in m.lower() for x in ["exp", "preview", "test", "experimental"])]
    pool = stable_candidates if stable_candidates else candidates

    # 2. Latest stable Flash model (flash in name, but not lite)
    flash_models = [m for m in pool if "flash" in m.lower() and "lite" not in m.lower()]
    if flash_models:
        flash_models.sort(key=extract_version_tuple, reverse=True)
        return flash_models[0]

    # 3. Latest stable Flash Lite model
    lite_models = [m for m in pool if "lite" in m.lower()]
    if lite_models:
        lite_models.sort(key=extract_version_tuple, reverse=True)
        return lite_models[0]

    # 4. Any stable model supporting generateContent
    if pool:
        pool.sort(key=extract_version_tuple, reverse=True)
        return pool[0]

    return env_model or "gemini-2.5-flash"

def generate_viral_script(topic="health", channel_context="", api_key=None, feedback=None, language="en", history=None):
    """
    実行役: 動画の台本を生成する。
    """
    global _cached_selected_model

    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_KEY")

    if api_key:
        genai.configure(api_key=api_key)

    if not _cached_selected_model:
        available_models = get_available_gemini_models()
        print(f"[Gemini Discovery] Available models: {available_models}")
        _cached_selected_model = select_best_model(available_models)
        print(f"[Gemini Discovery] Selected model: {_cached_selected_model}")

    current_model_name = _cached_selected_model
    model = genai.GenerativeModel(current_model_name)

    if history is None:
        history_file = "generated_history.json"
        if not os.path.exists(history_file):
            try:
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        else:
            history = []

    history_section = ""
    if history:
        recent_items = history[-50:]
        covered_list = []
        for item in recent_items:
            if isinstance(item, dict):
                t_title = item.get("title", "")
                t_topic = item.get("topic", "")
                entry = f"Title: {t_title}" if t_title else ""
                if t_topic:
                    entry += f" (Topic: {t_topic})" if entry else f"Topic: {t_topic}"
                if entry:
                    covered_list.append(f"- {entry}")
            elif isinstance(item, str):
                covered_list.append(f"- {item}")
        if covered_list:
            history_section = f"""
        === RECENTLY COVERED LOCATIONS/TOPICS (NEVER REPEAT OR DUPLICATE THESE) ===
        {chr(10).join(covered_list)}
        ===========================================================================
        """

    selected_hook = random.choice(HOOK_PATTERNS)
    hook_instruction = selected_hook["instruction"]
    print(f"[HOOK_TRIGGER] Selected hook pattern: {selected_hook['type']}")

    feedback_section = ""
    if feedback:
        feedback_section = f"""
        === FEEDBACK FROM AUDITOR/SYSTEM (PLEASE FIX THESE POINTS) ===
        {feedback}
        ==============================================================
        """

    if language == "ja":
        prompt = f"""
        あなたはプロのYouTubeショート動画プロデューサーです。日本の視聴者向けに。
        以下のトピックについて、15秒のバイラルな台本を作成してください。
        
        トピック: {topic}
        {channel_context}
        
        {feedback_section}
        {history_section}
        
        === 構成ルール（Ultra-Tight 15s Golden Ratio） ===
        1. 【0〜3秒：フック】{hook_instruction}（語尾を上げるイントネーションや問いかけ、衝撃的な主張で引き込むこと）。
        2. 【3〜12秒：コア】意外な事実や雑学の核心を、短い2つの文（2セクション）でテンポよく伝えること。
        3. 【12〜15秒：結び】必ず「みんなは知ってた？」「コメントで教えてね！」等のコメント誘導、または強い共感文（1文）で締めること。
        
        === 厳守ルール ===
        - 【超重要・総文字数の絶対上限】総文字数は必ず「60文字〜75文字」の間（スペース・改行を除く）に厳密に収めてください。これ以上短い、または長い台本は完全禁止とします（1文字でも超えればエラーとみなします）。
        - 【テロップ細分化（シーン切り替え）】15秒の中でテロップ（文）が「4回〜5回」に細かく分割されるよう、必ず「フック（1文）？＋コア（短い2文）＋結び（1文）！」という合計4文の構成で作成してください。
        - 自然な日本語。絵文字は使用しないこと。
        - 視聴者が賢くなったと感じる「雑学」のトーンにすること。
        
        Title: [バイラルなタイトル]
        Content:
        [強力なフック質問文]？ [意外な事実のコア文1]。 [雑学の納得コア文2]。 [コメント誘導または共感の結び文]！
        PexelsKeyword: [映像検索用の英語キーワード。動物や地理のテーマを必ず含めること]
        """
    else:
        prompt = f"""
        You are a professional YouTube Shorts producer for an English channel.
        Create an extremely fast, high-impact 15-second viral script.
        
        Topic: {topic}
        {channel_context}
        
        {feedback_section}
        {history_section}
        
        === STRUCTURE (Ultra-Tight 15s Golden Ratio) ===
        1. [0-3s: Hook] {hook_instruction}
           - AVOID cliches like "Did you know...?" or "What if I told you...?"
        2. [3-12s: Core] Deliver the surprising facts or core insight in exactly two ultra-short, action-oriented sentences. Strip away unnecessary adjectives and adverbs. Keep it under 12 seconds total.
        3. [12-15s: Closing] End with a short, comment-triggering question or strong empathetic call (1 sentence, e.g., "Think so? Comment below!", "What do you think?").
        
        === STRICT RULES ===
        - [STRICT WORD COUNT] Total word count MUST be strictly between 30 to 37 words max to ensure it easily reads within 12-13 seconds. Absolutely NO exceptions (not even a single word over).
        - [SCENE SEGMENTATION (4-5 Cuts)] Ensure the script is written in exactly 4 very short sentences (Hook + 2 Core Sentences + Closing) so that the video caption divides into 4 dynamic text changes, preventing static screens.
        - No emojis. Natural tone.
        
        === OUTPUT FORMAT ===
        Title: [Viral Title]
        Content:
        [Short Hook Question]? [Punchy Core Sentence 1]. [Punchy Core Sentence 2]. [Comment-triggering Closing Sentence]!
        PexelsKeyword: [English keyword for video search. Must include the core theme]
        """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
    except Exception as e:
        err_str = str(e).lower()
        retry_triggers = ["not_found", "not found", "404", "deprecated", "unavailable", "429", "resource_exhausted", "quota"]
        if any(trigger in err_str for trigger in retry_triggers):
            print(f"[Gemini Fallback] Error with model '{current_model_name}': {e}")
            available_models = get_available_gemini_models()
            fallback_model_name = select_best_model(available_models, exclude_models={current_model_name})
            print(f"[Gemini Fallback] Fallback model: {fallback_model_name}")
            _cached_selected_model = fallback_model_name
            fallback_model = genai.GenerativeModel(fallback_model_name)
            response = fallback_model.generate_content(prompt)
            text = response.text
        else:
            print(f"FATAL: Gemini Generation Error: {e}")
            raise

    # Titleの抽出（大文字小文字を区別せず、最悪の場合のフォールバックを徹底）
    title_match = re.search(r"(?:Title|TITLE):\s*(.*)", text)
    title = title_match.group(1).strip() if title_match else f"Insights on {topic}"
    
    # Contentの抽出（Content: から PexelsKeyword: までの間を正確に切り出す）
    content_match = re.search(r"(?:Content|CONTENT):\s*(.*?)(?=(?:PexelsKeyword|PEXELS|\Z))", text, re.DOTALL)
    if content_match and content_match.group(1).strip():
        content = content_match.group(1).strip()
    else:
        # 抽出失敗時の3秒フォールバックを阻止、テキスト全体からゴミを削って台本とする
        content = text.replace(f"Title: {title}", "").strip()

    # PexelsKeywordの抽出
    keyword_match = re.search(r"(?:PexelsKeyword|Pexels|KEYWORDS):\s*(.*)", text, re.IGNORECASE)
    keyword = "nature" if language != "ja" else "animal"
    if keyword_match:
        keyword = keyword_match.group(1).strip()
        # 台本側に入り込んだキーワード行を完全に消去
        content = content.replace(keyword_match.group(0), "").strip()
        
    return title, content, keyword
