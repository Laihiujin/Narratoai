import os
import json
import time
import streamlit as st
from loguru import logger

from app.config import config
from app.utils import utils, video_processor
from app.services.prompts import PromptManager
from webui.tools.base import create_vision_analyzer


def generate_ddz_highlights(params):
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(p, m=""):
        progress_bar.progress(p)
        status_text.text(m or f"进度: {p}%")

    try:
        with st.spinner("正在识别斗地主高光事件..."):
            if not params.video_origin_path:
                st.error("请先选择视频文件")
                return

            update_progress(10, "提取关键帧...")
            keyframes_dir = os.path.join(utils.temp_dir(), "keyframes")
            video_hash = utils.md5(params.video_origin_path + str(os.path.getmtime(params.video_origin_path)))
            video_keyframes_dir = os.path.join(keyframes_dir, video_hash)
            os.makedirs(video_keyframes_dir, exist_ok=True)

            keyframe_files = []
            for filename in sorted(os.listdir(video_keyframes_dir)):
                if filename.endswith('.jpg'):
                    keyframe_files.append(os.path.join(video_keyframes_dir, filename))

            if not keyframe_files:
                vp = video_processor.VideoProcessor(params.video_origin_path)
                vp.extract_frames_by_interval_ultra_compatible(
                    output_dir=video_keyframes_dir,
                    interval_seconds=st.session_state.get('frame_interval_input', 3)
                )
                for filename in sorted(os.listdir(video_keyframes_dir)):
                    if filename.endswith('.jpg'):
                        keyframe_files.append(os.path.join(video_keyframes_dir, filename))

            if not keyframe_files:
                st.error("未提取到关键帧")
                return

            update_progress(30, "初始化视觉分析器...")
            vision_provider = (st.session_state.get('vision_llm_provider') or config.app.get('vision_llm_provider', 'litellm')).lower()
            vision_api_key = st.session_state.get(f'vision_{vision_provider}_api_key') or config.app.get(f'vision_{vision_provider}_api_key')
            vision_model = st.session_state.get(f'vision_{vision_provider}_model_name') or config.app.get(f'vision_{vision_provider}_model_name')
            vision_base_url = st.session_state.get(f'vision_{vision_provider}_base_url') or config.app.get(f'vision_{vision_provider}_base_url', '')

            if not vision_api_key or not vision_model:
                st.error("未配置视觉模型")
                return

            analyzer = create_vision_analyzer(
                provider=vision_provider,
                api_key=vision_api_key,
                model=vision_model,
                base_url=vision_base_url
            )

            ddz_rules = (
                "玩法是这样的：芒果斗地主的‘吹牛王’玩法是基于斗地主规则的变种，加入了一个类似吹牛的环节。"
                "玩家出牌时可以‘报点’虚张声势，如喊出‘两张A’但实际是两张K。其他玩家可以选择‘抢牌’或‘揭穿’，"
                "揭穿成功有奖励，揭穿失败有惩罚；最先出完手牌者获胜。"
            )
            prompt = PromptManager.get_prompt(
                category="game_ddz_blow_king",
                name="highlight_detection",
                parameters={"rules_summary": ddz_rules}
            )

            update_progress(50, "分析关键帧...")
            results = st.session_state.get('vision_batch_size') or config.frames.get("vision_batch_size", 10)
            results = analyzer.analyze_images(
                images=keyframe_files,
                prompt=prompt,
                batch_size=results
            )

            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            analysis = loop.run_until_complete(results)
            loop.close()

            update_progress(70, "解析结果...")
            merged = {"items": []}
            from webui.tools.generate_short_summary import parse_and_fix_json
            for r in analysis:
                if isinstance(r, dict) and 'response' in r:
                    content = r['response']
                else:
                    content = r
                data = parse_and_fix_json(content)
                if data and isinstance(data, dict) and 'items' in data:
                    # 转换为视频脚本格式
                    for idx, item in enumerate(data['items'], start=len(merged["items"]) + 1):
                        ts = item.get("timestamp", "00:00:00,000-00:00:00,000")
                        et = item.get("event_type", "highlight")
                        desc = item.get("description", "")
                        merged["items"].append({
                            "_id": idx,
                            "timestamp": ts,
                            "picture": f"{et}: {desc}",
                            "narration": desc,
                            "OST": 2
                        })

            if not merged["items"]:
                st.error("未识别到高光事件")
                return

            save_dir = os.path.join(utils.script_dir())
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, "ddz_highlights.json")
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(merged["items"], f, ensure_ascii=False, indent=2)

            st.session_state['video_clip_json'] = merged["items"]
            st.session_state['video_clip_json_path'] = save_path
            update_progress(100, "识别完成")
            st.success("已生成斗地主高光脚本")

    except Exception as e:
        progress_bar.progress(100)
        st.error(str(e))
        logger.exception(str(e))
