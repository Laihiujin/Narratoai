from app.services.prompts.base import PromptMetadata, ParameterizedPrompt, ModelType, OutputFormat


class DDZHighlightPrompt(ParameterizedPrompt):
    def __init__(self):
        metadata = PromptMetadata(
            name="highlight_detection",
            category="game_ddz_blow_king",
            version="1.0.0",
            description="检测斗地主吹牛王玩法高光事件",
            model_type=ModelType.MULTIMODAL,
            output_format=OutputFormat.JSON,
            tags=["game", "ddz", "highlights"],
            parameters=["rules_summary"]
        )
        super().__init__(metadata, required_parameters=["rules_summary"])

    def get_template(self) -> str:
        return (
            "你将分析一组按时间顺序的游戏画面帧，游戏为斗地主的‘吹牛王’变种。"
            "规则摘要：\n${rules_summary}\n"
            "请识别符合下列高光事件：\n"
            "1) 成功揭穿：判断为说谎且揭穿者正确；\n"
            "2) 揭穿失败：揭穿者判断错误；\n"
            "3) 关键抢牌：抢牌后显著阻断对手节奏；\n"
            "4) 关键终结：玩家率先出完手牌或形成决定性优势；\n"
            "5) 亮眼组合：明显强力出牌（如炸弹、顺子、飞机等）扭转局势。\n"
            "输出严格的JSON：{\n"
            "  \"items\": [\n"
            "    {\n"
            "      \"timestamp\": \"HH:MM:SS,mmm-HH:MM:SS,mmm\",\n"
            "      \"event_type\": \"success_callout|failed_callout|key_block|finish|power_combo\",\n"
            "      \"description\": \"简要说明事件和判据\",\n"
            "      \"confidence\": 0.0\n"
            "    }\n"
            "  ]\n"
            "}"
        )

