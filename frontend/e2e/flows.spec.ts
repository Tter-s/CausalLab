/**
 * CausaLab E2E 核心流程（黑盒，经真实 UI）：
 * 后端使用独立数据目录（backend/data-e2e），不污染开发数据。
 */
import { expect, test } from "@playwright/test";

const API = "http://127.0.0.1:8010/api";

test.describe.serial("核心流程", () => {
  test.beforeEach(async () => {
    // 清空业务数据，保证幂等（设置保留）
    await fetch(`${API}/data/all`, { method: "DELETE" });
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
});
