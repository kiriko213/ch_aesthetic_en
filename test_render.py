import asyncio
import os
from auto_main import run_auto_post

async def test_full_production():
    print("=== GlobeGuess 本番シミュレーション（アップロードなし）開始 ===")
    
    # テスト用のトピックを指定（サントリーニ島）
    topic = "Santorini Greece"
    
    # run_auto_post を実行するが、内部でアップロードをスキップするようにパッチを当てるか、
    # 簡易的なテスト用ロジックで動かす
    # ここでは、auto_main のロジックをベースに「動画生成完了」までを実行します。
    
    import ai_generator
    import generate_video
    from main import load_config
    
    config = load_config()
    p = config["aesthetic_en"]
    
    # 1. 台本生成
    print(f"1. 台本生成中... (Topic: {topic})")
    title, script = ai_generator.generate_viral_script(topic)
    print(f"   [Title]: {title}")
    print(f"   [Script]:\n{script}")
    
    # 2. 動画生成
    output_fn = "test_globeguess_production.mp4"
    if os.path.exists(output_fn): os.remove(output_fn)
    
    print("2. 動画レンダリング中... (数分かかります)")
    bg_path = "temp_bg.mp4"
    bgm_path = p["bgm"]
    
    # generate_video を呼び出す
    # pexels_query は台本から抽出
    import re
    query_match = re.search(r"PexelsKeyword:\s*(.*)", script)
    pexels_query = query_match.group(1).strip() if query_match else topic
    
    result_fn = await generate_video.make_short_video(
        script, 
        bg_path, 
        bgm_path, 
        output_filename=output_fn,
        voice=p["voice"],
        pexels_key=p["pexels_api_key"],
        topic=topic,
        pexels_query=pexels_query
    )
    
    print(f"=== シミュレーション完了 ===")
    print(f"生成されたファイル: {result_fn}")
    print("このファイルが意図通り（字幕が下部、映像が正確など）であれば、本番環境も100%成功します。")

if __name__ == "__main__":
    asyncio.run(test_full_production())
