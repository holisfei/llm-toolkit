# Agent loop 

Agent = 模型在一个循环里自主使用工具。

Workflow 和 Agent 的本质区别:控制流谁说了算。 
- Workflow 是你画好流程图、模型填空
- Agent 是模型自己决定流程图长什么样。前面几天做的"调一次 tool → 拼回去 → 再问一次"是手动驱动的两轮


agent loop:

```py
def agent_run(user_message, tools):
    messages = [user_message]          # 对话历史 = 事件队列
    
    while True:                         # ← 这个 while 就是 agent 的全部魔法
        response = llm(messages, tools)  # 问模型: 看着现在的历史, 你想干嘛?
        
        # 1: 模型可能"想调工具", 也可能"直接给最终答案了"
        # 你怎么区分这两种? type=tool_use, delta.tool_calls
        
        if response.tool_calls:
            # 2: 执行工具: dispatch_all 执行多个工具
            results = dispatch_all(tools)
            # 3: 把"模型的工具请求"和"工具结果"都拼回 messages
            append_tool_round(messages, response, results)
            # 4: 然后呢? 循环回到顶部, 再问模型 -- 但这一步是"自动"的,
            #         不是你手动再调一次. 这就是 agent 和 workflow 的分界线.
            continue
        else:
            # 5: 模型不调工具了, 说明它给出最终答案了, 退出循环
            return response.text
```

# Anki

Q1: 对照上面这个 while 循环,前面 D4–D6 手动做的"调 tool → 拼回去 → 再问一次"——缺了哪一步,导致它还是 workflow 不是 agent?
A：缺少了自动循环再次向LLM发messages，之前的逻辑都是手动写死的2轮且都是手动调用LLM

Q2: 这个 while True 如果不加任何别的条件,会出什么事?这引出了哪些终止条件?你能想到几个?
A：while True 没有任何东西能停下来——它会一直烧钱、烧 token,直到你手动 kill 或者撞 API 限额。 这是 agent 最经典的事故。所以需要终止条件：
- max_iterations(最多循环 N 轮)
- 正常结束(模型不再调工具,给出 final answer)
- token/成本预算超限
- 工具连续失败 N 次

Q3: iOS 经验里,什么东西和这个 while + 处理事件 + 决定继续还是退出 的结构最像?
A：类似于iOS的runloop机制

agent                    runloop
messages(对话历史)        事件队列
llm(messages, tools)     getNextEvent()——但事件不是用户产生的,是模型生成的下一个动作
模型返回 tool_call        来了一个 input source 事件,要 process
dispatch_all             执行工具process(event)——处理这个事件
工具结果拼回 messages      处理结果重新入队,等下一轮
模型给 final answer(不再调工具) running = false,RunLoop 退出
max_iterations            RunLoop 的超时/最大迭代保护(防止 runaway loop)

RunLoop 的事件来自外部(用户点击、网络回调、timer)。Agent loop 的"事件"来自模型自己——模型看着历史,生成下一个该干的动作


Workflow vs Agent 的分界 = 控制流谁定。 
- 你写死步数 = workflow
- 模型自己决定走几步 = agent。那行 while 是全部魔法。

while True 的自主决定权 必须设置 终止循环的条件。 
- 设置终止条件不是为正常结束(那是模型没有工具可调用), 而是为"模型不肯停时强制让其停下来"。
- 最关键的是 max_iterations，没有它, agent 是个可能无限烧钱的死循环。事件的循环源头是模型自己决策的。

