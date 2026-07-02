# crisis_gate.py
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv
load_dotenv()

client = ContentSafetyClient(
    endpoint=os.getenv("CONTENT_SAFETY_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("CONTENT_SAFETY_KEY"))
)

def check_crisis(text: str) -> dict:
    """
    반환:
      is_crisis (bool): True → RAG 중단, kfsp_centers 핫라인 안내
      severity (int): 0~6 (높을수록 위험)
      categories (list): 감지된 카테고리 목록
    임계값(severity >= 2, max >= 4)은 ASIST 매뉴얼 p49~51 참고 후 팀 논의로 조정.
    """
    request = AnalyzeTextOptions(
        text=text,
        categories=[TextCategory.SELF_HARM, TextCategory.HATE, TextCategory.VIOLENCE],
        output_type="FourSeverityLevels"
    )
    response = client.analyze_text(request)

    max_severity = 0
    triggered = []
    for item in response.categories_analysis:
        if item.severity >= 2:
            triggered.append(item.category)
            max_severity = max(max_severity, item.severity)

    is_crisis = TextCategory.SELF_HARM in triggered or max_severity >= 4

    return {
        "is_crisis": is_crisis,
        "severity": max_severity,
        "categories": triggered
    }

if __name__ == "__main__":
    print(check_crisis("오늘 학교에서 발표했는데 잘 안 됐어"))
    # → {"is_crisis": False, "severity": 0, "categories": []}

    print(check_crisis("죽고 싶어"))
    # → {"is_crisis": True, ...}