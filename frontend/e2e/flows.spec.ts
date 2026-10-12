/**
 * CausaLab E2E 核心流程（黑盒，经真实 UI）：
 * 后端使用独立数据目录（backend/data-e2e），不污染开发数据。
 */
import { expect, test } from "@playwright/test";

const API = "http://127.0.0.1:8010/api";

test.describe.serial("核心流程", () => {
  test.beforeEach(async () => {
    // 清空业务数据，保证幂等（设置保留）；若上一用例遗留启用的密码保护则先关闭
    await fetch(`${API}/auth/disable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: "e2e-pass-123" }),
    }).catch(() => {});
    await fetch(`${API}/data/all`, { method: "DELETE" }).catch(() => {});
  });

  test("仪表盘显示真实统计与模块导航", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "概览" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("待复盘决策")).toBeVisible();
    await expect(page.getByText("阻塞任务")).toBeVisible();
    // 四个核心模块 + 三个跨模块能力都在导航中
    for (const nav of ["知识债务", "记忆实验室", "决策时间机", "任务复盘", "证据时间线", "假设实验室", "改进循环"]) {
      await expect(page.locator("aside").getByText(nav)).toBeVisible();
    }
  });

  test("决策时间机：创建决策 → 添加预测 → 揭晓 → 快照不变", async ({ page }) => {
    await page.goto("/dtm", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("button", { name: /记录决策/ })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: /记录决策/ }).click();
    await page.getByPlaceholder("如：考研还是就业").fill("E2E 测试决策：选笔记本还是台式机");
    await page.getByPlaceholder("当时的环境与约束").fill("预算 8000，主要写代码");
    const dialog = page.getByRole("dialog");
    await dialog.locator("input").nth(2).fill("笔记本"); // 备选 A
    await dialog.locator("input").nth(3).fill("台式机"); // 备选 B
    await page.getByRole("button", { name: "保存" }).click();
    await expect(page.getByText("E2E 测试决策：选笔记本还是台式机")).toBeVisible();

    // 进入详情
    await page.getByText("E2E 测试决策：选笔记本还是台式机").click();
    await expect(page.getByRole("heading", { name: /E2E 测试决策/ })).toBeVisible();
    await expect(page.getByText("笔记本").first()).toBeVisible();

    // 添加预测
    await page.getByRole("tab", { name: "预测与校准" }).click();
    await page.getByPlaceholder(/初试过线的概率/).fill("台式机性价比更高的概率");
    await page.locator('input[type="range"]').fill("70");
    await page.getByRole("button", { name: /记录预测/ }).click();
    await expect(page.getByText("70%").first()).toBeVisible();

    // 揭晓
    page.once("dialog", (d) => d.accept("预算涨价了"));
    await page.getByRole("button", { name: "命中", exact: true }).click();
    await expect(page.getByText("命中", { exact: true }).first()).toBeVisible();

    // 快照历史：创建时 1 个，不可修改
    await page.getByRole("tab", { name: "快照历史" }).click();
    await expect(page.getByText(/不可覆盖快照/)).toBeVisible();
    await expect(page.getByText("创建时")).toBeVisible();
  });

  test("任务复盘：创建项目与任务 → 记录阻塞 → 统计更新", async ({ page }) => {
    await page.goto("/ta", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("button", { name: /新建项目/ }).first()).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: /新建项目/ }).first().click();
    const projDialog = page.getByRole("dialog");
    await projDialog.locator("input").first().fill("E2E 测试项目");
    await projDialog.getByRole("button", { name: "创建" }).click();
    await expect(page.getByText("E2E 测试项目")).toBeVisible();

    await page.getByText("E2E 测试项目").click();
    await page.getByRole("button", { name: /新建任务/ }).first().click();
    const taskDialog = page.getByRole("dialog");
    await taskDialog.locator("input").first().fill("E2E 写爬虫");
    await taskDialog.locator('input[type="number"]').first().fill("5");
    await taskDialog.getByRole("button", { name: "创建" }).click();
    await expect(page.getByText("E2E 写爬虫").first()).toBeVisible();

    // 状态 → 进行中，然后记录阻塞事件
    const row = page.locator("div").filter({ hasText: "E2E 写爬虫" }).locator("select").first();
    await row.selectOption("doing");
    await page.getByRole("button", { name: /记录事件/ }).click();
    const evDialog = page.getByRole("dialog");
    await evDialog.getByPlaceholder(/发生了什么/).fill("目标网站改版，需要重新分析");
    await evDialog.locator('input[type="number"]').last().fill("90");
    await evDialog.getByRole("button", { name: "记录", exact: true }).click();
    await expect(page.getByText("目标网站改版，需要重新分析").first()).toBeVisible();

    // 统计 tab 出现阻塞分钟
    await page.getByRole("tab", { name: "统计" }).click();
    await expect(page.getByText("1.5 小时").first()).toBeVisible();
  });

  test("记忆实验室：建卡 → 复习 → 间隔调度生效", async ({ page }) => {
    await page.goto("/ml", { waitUntil: "domcontentloaded" });
    // 卡组
    await expect(page.getByRole("tab", { name: "卡片管理" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("tab", { name: "卡片管理" }).click();
    await page.getByPlaceholder("卡组名称").fill("E2E 卡组");
    await page.getByRole("button", { name: "创建", exact: true }).first().click();
    await expect(page.getByText("E2E 卡组").first()).toBeVisible();
    // 卡片
    await page.locator("select").first().selectOption({ label: "E2E 卡组" });
    await page.getByPlaceholder("正面（问题/提示）").fill("E2E 正面问题");
    await page.getByPlaceholder("背面（答案）").fill("E2E 背面答案");
    await page.getByRole("button", { name: /添加卡片/ }).click();

    // 复习
    await page.getByRole("tab", { name: "复习" }).click();
    await expect(page.getByText("E2E 正面问题").first()).toBeVisible();
    await page.getByRole("button", { name: /显示答案/ }).first().click();
    await expect(page.getByText("E2E 背面答案").first()).toBeVisible();
    await page.getByRole("button", { name: /有点费劲/ }).first().click();
    // 复习后应显示成功提示（sonner toast）
    await expect(page.getByText(/已记录：下次|已进入学习步骤|毕业！/)).toBeVisible({ timeout: 10_000 });
  });

  test("知识债务：答题一次不下结论（护栏），纠正可用", async ({ page }) => {
    await page.goto("/kd", { waitUntil: "domcontentloaded" });
    await expect(page.getByPlaceholder("学科名称，如：高等数学")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder("学科名称，如：高等数学").fill("E2E 学科");
    await page.getByRole("button", { name: /创建学科/ }).click();
    await page.getByLabel("知识点所属学科").selectOption({ label: "E2E 学科" });
    await page.getByPlaceholder("知识点名称").fill("E2E 知识点");
    await page.getByRole("button", { name: /创建知识点/ }).click();
    await expect(page.getByText("E2E 知识点").first()).toBeVisible();

    // 任务与答题
    await page.getByRole("tab", { name: /学习任务与诊断/ }).click();
    await page.locator("nav + div, body").getByText("E2E 知识点").first().click();
    await page.getByPlaceholder("任务标题，如：手推梯度下降更新公式").fill("E2E 练习题");
    await page.getByRole("button", { name: /添加任务/ }).click();
    await expect(page.getByText("E2E 练习题").first()).toBeVisible();

    // 记录一次错误答题
    await page.getByLabel("记录答题").first().click();
    await page.getByRole("button", { name: /提交答题记录/ }).first().click();
    await expect(page.getByText("答题已记录")).toBeVisible();

    // 规则诊断：一次失败必须输出“样本不足”
    await page.getByRole("button", { name: "规则诊断" }).first().click();
    await expect(page.getByText(/样本不足/).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/不足以支持任何能力缺陷判断|样本不足以支持/).first()).toBeVisible();
  });

  test("证据时间线：跨模块事件出现且可筛选", async ({ page }) => {
    // beforeEach 清空了数据，这里自建一条决策以产生 dtm 事件
    await fetch(`${API}/dtm/decisions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "E2E 时间线决策", options: [] }),
    });
    await page.goto("/timeline", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/创建决策/).first()).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "决策时间机", exact: true }).click();
    await expect(page.getByText("E2E 时间线决策").first()).toBeVisible();
  });

  test("设置：无 AI 模式提示与 Provider 表单可用", async ({ page }) => {
    await page.goto("/settings", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Provider 配置/)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/所有 AI 请求经本服务端代理/)).toBeVisible();
    await expect(page.getByText("本月用量")).toBeVisible();
  });

  test("认证：启用后强制登录，设置页可关闭", async ({ page }) => {
    // 通过 API 启用密码保护
    const setup = await fetch(`${API}/auth/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: "e2e-pass-123" }),
    });
    expect(setup.status).toBe(201);

    // 打开任意页 → 被重定向到登录页
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForURL("**/login", { timeout: 15_000 });
    await expect(page.getByText(/请输入访问密码|Enter your access password/)).toBeVisible({ timeout: 15_000 });

    // 错误密码提示
    await page.locator("#login-password").fill("wrong-pass-9");
    await page.getByRole("button", { name: /解锁|Unlock/ }).click();
    await expect(page.getByText(/密码错误|Wrong password/)).toBeVisible({ timeout: 10_000 });

    // 正确密码 → 进入仪表盘
    await page.locator("#login-password").fill("e2e-pass-123");
    await page.getByRole("button", { name: /解锁|Unlock/ }).click();
    await page.waitForURL("**/", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "概览" })).toBeVisible({ timeout: 30_000 });

    // 设置 → 安全 → 关闭密码保护
    await page.goto("/settings", { waitUntil: "domcontentloaded" });
    await page.getByRole("tab", { name: /安全|Security/ }).click();
    await page.getByPlaceholder(/当前密码|Current password/).last().fill("e2e-pass-123");
    await page.getByRole("button", { name: /确认关闭|Disable/ }).click();
    await expect(page.getByText(/密码保护已关闭|Password protection disabled/)).toBeVisible({ timeout: 10_000 });

    // 关闭后无需登录
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "概览" })).toBeVisible({ timeout: 30_000 });
  });

  test("知识债务：上传题目与解答附件 → 出现在列表 → 可删除", async ({ page }) => {
    await page.goto("/kd", { waitUntil: "domcontentloaded" });
    await expect(page.getByPlaceholder("学科名称，如：高等数学")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder("学科名称，如：高等数学").fill("E2E 附件学科");
    await page.getByRole("button", { name: /创建学科/ }).click();
    await page.getByLabel("知识点所属学科").selectOption({ label: "E2E 附件学科" });
    await page.getByPlaceholder("知识点名称").fill("E2E 附件知识点");
    await page.getByRole("button", { name: /创建知识点/ }).click();
    await expect(page.getByText("E2E 附件知识点").first()).toBeVisible();

    // 切到「学习任务与诊断」并选中知识点（附件卡片在此标签页内）
    await page.getByRole("tab", { name: /学习任务与诊断/ }).click();
    await page.locator("nav + div, body").getByText("E2E 附件知识点").first().click();
    await expect(page.getByText("题目与解答附件")).toBeVisible({ timeout: 10_000 });

    // 空状态
    await expect(page.getByText("这个知识点还没有附件")).toBeVisible();

    // 上传「题目」附件（真实 file input）
    await page.getByLabel("附件类型").selectOption({ label: "题目" });
    await page.getByLabel("附件文件").setInputFiles({
      name: "E2E-题目.png",
      mimeType: "image/png",
      buffer: Buffer.from("89504e470d0a1a0a", "hex"),
    });
    await page.getByRole("button", { name: /上传附件/ }).click();
    await expect(page.getByText("附件已上传")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("E2E-题目.png")).toBeVisible();

    // 再上传一个「我的解答」附件
    await page.getByLabel("附件类型").selectOption({ label: "我的解答" });
    await page.getByLabel("附件文件").setInputFiles({
      name: "E2E-解答.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\n% e2e\n"),
    });
    await page.getByRole("button", { name: /上传附件/ }).click();
    await expect(page.getByText("E2E-解答.pdf")).toBeVisible({ timeout: 15_000 });

    // 两个附件都在，且类型标签区分正确
    await expect(page.getByText("E2E-题目.png")).toBeVisible();
    await expect(page.getByText("E2E-解答.pdf")).toBeVisible();

    // 上传事件进入统一时间线
    const events = await fetch(`${API}/timeline?module=kd&limit=50`).then((r) => r.json());
    expect(events.items.some((e: { event_type: string }) => e.event_type === "attachment.uploaded")).toBe(true);

    // 删除第二个附件
    await page.getByRole("button", { name: "删除附件" }).nth(1).click();
    await expect(page.getByText("附件已删除")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("E2E-解答.pdf")).toHaveCount(0);
    await expect(page.getByText("E2E-题目.png")).toBeVisible();
  });

  test("设置：按任务类型指定模型的输入区可用且能保存", async ({ page }) => {
    await page.goto("/settings", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("按任务类型指定模型（可选）")).toBeVisible({ timeout: 30_000 });
    // 八个任务类型都在
    for (const label of ["知识诊断", "学习建议", "项目复盘", "决策复盘", "反事实推演", "实验设计", "循环复盘", "通用"]) {
      await expect(page.getByText(label, { exact: true })).toBeVisible();
    }
    // 给「知识诊断」指定一个模型并保存
    await page.getByPlaceholder("模型 ID，如 deepseek-chat").first().fill("e2e-model-x");
    await page.getByRole("button", { name: /保存设置/ }).click();
    await expect(page.getByText("AI 设置已保存")).toBeVisible({ timeout: 10_000 });

    // 后端确实存下了这条覆盖
    const cfg = await fetch(`${API}/settings/ai`).then((r) => r.json());
    const row = cfg.task_models.find((m: { task_type: string }) => m.task_type === "kd_diagnosis");
    expect(row?.model_id).toBe("e2e-model-x");
  });
});
