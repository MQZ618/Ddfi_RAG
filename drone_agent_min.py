#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最少可行 LLM+VLM 具身无人机 —— 纯 Python 抽象仿真
不需要 Gazebo / PX4 / ROS，一个文件跑通"视觉感知(VLM)-决策(LLM)-执行-闭环"。

闭环：渲染顶视图相机画面 -> VLM 识别障碍物 -> LLM 规划航点 -> 移动执行
      -> 撞障碍/未到达 -> 重新"看"、重新规划。

用法：
  配 key：LLM_KEY=sk-xxx LLM_BASE=https://xxx LLM_MODEL=gpt-4o-mini VLM_MODEL=gpt-4o-mini \
          python3 drone_agent_min.py
  不配 key：python3 drone_agent_min.py（启发式兜底，流程照跑）
  消融实验：PERCEPTION=oracle|vlm|none python3 drone_agent_min.py
"""
import os, json, math, random, io, base64

SPEED = 2.0          # 每步移动距离
MAX_STEPS = 400      # 单场景最大步数
N_OBSTACLES = 8      # 障碍物数量

# ---------------- 1. 世界（仿真环境） ----------------
def make_world(seed):
    rnd = random.Random(seed)
    return {
        "size": (100.0, 100.0),
        "start": (5.0, 5.0),
        "target": (95.0, 95.0),
        "obstacles": [
            {"x": rnd.uniform(20, 80), "y": rnd.uniform(20, 80), "r": rnd.uniform(5, 12)}
            for _ in range(N_OBSTACLES)
        ],
    }

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def inside_obstacle(world, p):
    return any(dist(p, (o["x"], o["y"])) < o["r"] for o in world["obstacles"])

def obstacles_text(obs):
    return ", ".join(f"({o['x']:.0f},{o['y']:.0f},r={o['r']:.0f})" for o in obs)

# ---------------- 2. 眼睛：渲染相机画面 + VLM 感知 ----------------
def render_view(world, pos):
    """把世界渲染成无人机顶视相机画面（绿点=无人机，红星=目标，灰圆=障碍物）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4, 4), dpi=72)
    for o in world["obstacles"]:
        ax.add_patch(plt.Circle((o["x"], o["y"]), o["r"], color="gray", alpha=0.6))
    ax.plot(*pos, "go", ms=8)
    ax.plot(*world["target"], "r*", ms=18)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_aspect("equal"); ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

VLM_PROMPT = """你是无人机视觉感知模块。图片是无人机顶视相机画面：绿点为无人机当前位置，红星为目标，灰色圆为障碍物。
请识别所有障碍物的圆心坐标和半径，只输出 JSON：{"obstacles": [{"x":..,"y":..,"r":..}]}，禁止输出其他任何文字。"""

def parse_obstacles(content):
    c = content.strip()
    if c.startswith("```"):
        c = c.split("\n", 1)[1] if "\n" in c else c[3:]
        c = c.rsplit("```", 1)[0].strip()
    data = json.loads(c)
    obs = data.get("obstacles", data) if isinstance(data, dict) else data
    out = []
    for o in obs[:N_OBSTACLES]:
        x, y, r = float(o["x"]), float(o["y"]), float(o["r"])
        if 0 <= x <= 100 and 0 <= y <= 100 and 0 < r <= 20:
            out.append({"x": x, "y": y, "r": r})
    return out

_client = None
def get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(
            api_key=os.environ.get("LLM_KEY", "none"),
            base_url=os.environ.get("LLM_BASE") or None,
        )
    return _client

def vlm_perceive(world, pos):
    """返回 VLM 识别出的障碍物列表；失败返回 None（由上层兜底）"""
    img_b64 = render_view(world, pos)
    try:
        r = get_client().chat.completions.create(
            model=os.environ.get("VLM_MODEL") or os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": [
                {"type": "text", "text": VLM_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ]}],
            temperature=0.0,
        )
        return parse_obstacles(r.choices[0].message.content)
    except Exception:
        return None

def perceive(world, pos):
    """感知入口：PERCEPTION=oracle(全知上界) / vlm(真实系统) / none(盲飞基线)"""
    mode = os.environ.get("PERCEPTION", "vlm" if os.environ.get("LLM_KEY") else "oracle")
    if mode == "none":
        return [], mode
    if mode == "vlm":
        obs = vlm_perceive(world, pos)
        # VLM 失败时回退全知坐标（论文里可记为感知失败率）
        return (obs if obs is not None else world["obstacles"]), mode
    return world["obstacles"], mode

# ---------------- 3. 大脑：LLM 航点规划 ----------------
PLAN_PROMPT = """你是无人机任务规划器。平面坐标系 0-100 x 0-100，起点 ({x0:.0f},{y0:.0f})，目标 ({xt:.0f},{yt:.0f})。
视觉感知到的圆形障碍物（圆心,半径）：{obs}
请规划 3-6 个安全中间航点，绕开所有障碍物到达目标。
只输出 JSON：{{"waypoints": [[x,y], ...]}}，禁止输出其他任何文字。"""

def parse_wps(content):
    c = content.strip()
    if c.startswith("```"):
        c = c.split("\n", 1)[1] if "\n" in c else c[3:]
        c = c.rsplit("```", 1)[0].strip()
    data = json.loads(c)
    wps = data.get("waypoints", data) if isinstance(data, dict) else data
    return [(float(x), float(y)) for x, y in wps[:6]]

def llm_plan(pos, world, obs):
    prompt = PLAN_PROMPT.format(x0=pos[0], y0=pos[1],
                                xt=world["target"][0], yt=world["target"][1],
                                obs=obstacles_text(obs) if obs else "无")
    try:
        r = get_client().chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return parse_wps(r.choices[0].message.content)
    except Exception:
        return []   # 解析/调用失败 -> 走兜底

def heuristic_plan(pos, world):
    """兜底：没 key 或 LLM 失败时用（直线 + 垂直绕行）"""
    t = world["target"]
    d = dist(pos, t)
    if d < 3:
        return [t]
    ux, uy = (t[0] - pos[0]) / d, (t[1] - pos[1]) / d
    cands = [(pos[0] + 15 * uy, pos[1] - 15 * ux),
             (pos[0] - 15 * uy, pos[1] + 15 * ux)]
    best = max(cands, key=lambda p: min(dist(p, (o["x"], o["y"])) for o in world["obstacles"]))
    return [best, t]

def planner(pos, world, obs):
    if os.environ.get("LLM_KEY"):
        wps = llm_plan(pos, world, obs)
        if wps:
            return wps
    return heuristic_plan(pos, world)

# ---------------- 4. 仿真主循环（闭环） ----------------
def run_episode(seed, plot=False):
    world = make_world(seed)
    pos = list(world["start"])
    tgt = world["target"]
    steps, replans = 0, 0
    path = [tuple(pos)]
    while steps < MAX_STEPS:
        obs, _ = perceive(world, pos)        # 感知：VLM 看画面 / 全知 / 盲飞
        wps = planner(pos, world, obs)       # 决策：LLM 规划航点
        replans += 1
        if not wps:
            continue
        blocked = False
        for wp in wps:                       # 执行：沿航点移动
            while dist(pos, wp) > 1.0:
                dx, dy = wp[0] - pos[0], wp[1] - pos[1]
                d = math.hypot(dx, dy) or 1.0
                nxt = (pos[0] + SPEED * dx / d, pos[1] + SPEED * dy / d)
                if inside_obstacle(world, nxt):   # 撞障碍 -> 重新感知+重规划
                    blocked = True
                    break
                pos = list(nxt)
                path.append(tuple(pos))
                steps += 1
                if dist(pos, tgt) < 3.0:          # 任务完成
                    if plot:
                        save_plot(world, path)
                    return {"success": True, "steps": steps, "replans": replans}
            if blocked:
                break
    if plot:
        save_plot(world, path)
    return {"success": False, "steps": steps, "replans": replans}

# ---------------- 5. 论文用图（可选） ----------------
def save_plot(world, path, fname="trajectory.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 6))
        for o in world["obstacles"]:
            ax.add_patch(plt.Circle((o["x"], o["y"]), o["r"], color="gray", alpha=0.6))
        xs, ys = zip(*path)
        ax.plot(xs, ys, "b-", lw=1.5, label="飞行轨迹")
        ax.plot(*world["start"], "go", ms=8, label="起点")
        ax.plot(*world["target"], "r*", ms=18, label="目标")
        ax.set_xlim(0, 100); ax.set_ylim(0, 100)
        ax.set_aspect("equal"); ax.legend()
        fig.savefig(fname, dpi=150)
        print(f"轨迹图已保存: {fname}")
    except ImportError:
        pass

# ---------------- 6. 批量实验（论文表格数据） ----------------
def main():
    n = int(os.environ.get("N_EPISODES", "20"))
    mode = os.environ.get("PERCEPTION", "vlm" if os.environ.get("LLM_KEY") else "oracle")
    print(f"=== LLM+VLM 具身无人机抽象仿真（{n} 场景，感知模式: {mode}）===")
    results = []
    for i in range(n):
        r = run_episode(i, plot=(i == 0))
        results.append(r)
        print(f"场景{i + 1:>2}: {'成功' if r['success'] else '失败'}  "
              f"步数={r['steps']:>3}  重规划={r['replans']}")
    ok = [r for r in results if r["success"]]
    print("-" * 44)
    print(f"任务完成率: {len(ok)}/{n} ({100 * len(ok) / n:.0f}%)")
    if ok:
        print(f"平均步数(成功): {sum(r['steps'] for r in ok) / len(ok):.1f}")
    print(f"平均重规划次数: {sum(r['replans'] for r in results) / n:.1f}")

if __name__ == "__main__":
    main()
