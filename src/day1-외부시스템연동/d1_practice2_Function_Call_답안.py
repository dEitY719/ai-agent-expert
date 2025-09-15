# 1. 계산기 함수 정의
def calculator(expression: str):
    """문자열 형태의 수학적 표현식을 계산하여 결과를 반환합니다."""
    print(f"계산기 함수에 입력될 표현식: {expression}")
    # 주의: eval()은 실제 프로덕션 환경에서는 신중하게 사용해야 합니다.
    return eval(expression)


# 모델 생성 (초기) - 이 부분은 tool call을 위해 아래에서 다시 정의됩니다.
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
)

generation_config = genai.GenerationConfig(temperature=0)

# 2. LLM에게 제공할 Tool 명세(Schema) 정의
calculator_func = FunctionDeclaration(
    name="calculator",
    description="수학적 표현식을 계산합니다. 예: '2+3*4'",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "계산할 수학 표현식 문자열. e.g., '(8 * 12) + (5 * 7)'",
            }
        },
        "required": ["expression"],
    },
)

# 3. Tool 객체 생성
calculator_tool = Tool(function_declarations=[calculator_func])

# 4. Tool을 포함하여 모델 다시 생성
model_with_tool = genai.GenerativeModel(
    model_name="gemini-1.5-flash", tools=[calculator_tool], generation_config=generation_config
)

# 5. 첫 번째 모델 호출 -> FunctionCall 응답 생성
response = model_with_tool.generate_content(prompt_1)
function_call = response.candidates[0].content.parts[0].function_call
print(f"모델이 요청한 함수 호출: {function_call}")

# 6. 모델이 요청한 함수 실행 및 결과 반환
if function_call.name == "calculator":
    expression = function_call.args["expression"]
    result = calculator(expression=expression)
    print(f"함수 실행 결과: {result}")

    # 7. 대화 기록을 만들어 모델에 다시 전달

    # 대화 기록 리스트를 생성합니다.
    conversation_history = [
        # [기록 1] 사용자의 최초 질문 (agent_executor의 첫 번째 항목)
        genai.protos.Content(role="user", parts=[genai.protos.Part(text=prompt_1)]),
        # [기록 2] 모델의 첫 응답 (FunctionCall 요청) (agent_executor의 두 번째 항목)
        response.candidates[0].content,
        # [기록 3] 함수 실행 결과 (agent_executor의 세 번째 항목)
        genai.protos.Content(
            role="user",
            parts=[
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=function_call.name, response={"content": str(result)}
                    )
                )
            ],
        ),
    ]

    # 전체 대화 기록을 전달하여 최종 답변 생성
    response_final = model_with_tool.generate_content(conversation_history)

    print(f"최종 답변: {response_final.text}")
