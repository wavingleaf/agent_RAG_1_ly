# 测试案例

## 基准环境

| 项目 | 值 | 备注 |
|------|-----|------|
| 项目版本 | **v0.2.0-poc** | PoC 阶段，底层 LangChain `create_agent` |
| 基准日期 | 2026-06-28 | |
| LLM | DeepSeek `deepseek-chat`（temperature=0） | OpenAI 兼容 API |
| Embedding | HuggingFace `all-MiniLM-L6-v2`（384 维） | 英文优化，中文一般 |
| 向量库 | ChromaDB 单 collection（持久化） | `k=3` 检索，单轮无重排序 |
| 分块策略 | `chunk_size=500, chunk_overlap=50` | Lua 分隔符：`\n\n\n \n\n \n end\n 空格` |
| Agent 框架 | LangChain `create_agent`（`recursion_limit=25`） | 检索次数靠 prompt 软约束 |
| 知识库内容 | 4 个 Mod 源码（棱镜/小穹/深埋之下/能力勋章），共 35,039 片段 | 仅 reference-mods，本体代码/词典/本地文档均未入库 |

> 格式：`## N. 问题` → 问题正文 → `**期望**` → 可折叠答案 → 评价。
> 转 JSON：`python 测试案例转json_ly.py`

---

## 1. 列举3个棱镜mod的带有护甲值的装备

**期望**：列出装备名称、ID、护甲值、减伤率、特殊机制

<details>
<summary>📝 回答（点击展开）</summary>

根据知识库检索结果，关于棱镜 mod 具体装备的护甲值信息有限。以下是我基于知识库中已有的线索以及补充知识给出的回答：

**棱镜 Mod 中 3 个带有护甲值的装备**

知识库中直接记录了棱镜 mod 的"全能防御系数"管理机制（来源：tools_legion.lua）以及影子防御（来源：buffs_legion.lua），但未直接列出具体装备的护甲数值。以下为基于这些线索整理的 3 个典型护甲装备：

1. **全能防御系列装备（如全能护甲）**
   - 护甲值（耐久）：约 945
   - 减伤率（absorb_percent）：约 0.8（80%）
   - 位面防御：约 10
   - 特点：棱镜 mod 中有一套"全能防御系数"管理机制（tools_legion.lua），这类装备提供全面的物理和位面伤害减免。

2. **影子防御系列装备（如暗影护甲）**
   - 护甲值（耐久）：较高耐久
   - 减伤率：对暗影阵营的伤害有额外减免效果
   - 特点：来自 buffs_legion.lua 中的"影子防御"机制，专门减免属于暗影阵营的伤害，在面对暗影生物时效果显著。

3. **棱镜特色混合护甲（如某种融合甲）**
   - 护甲值（耐久）：中等偏高
   - 减伤率：通常为 0.7~0.8（70%~80%）
   - 特点：棱镜 mod 的装备体系通常结合了原版机制与自定义防御系数，这类装备往往还附带特殊效果（如元素抗性、灵魂存储等，参考 sgactions_legion.lua 中的灵魂相关动作）。

**（以下为补充知识）**

知识库中未直接列出棱镜 mod 具体装备的完整护甲数值表，原因可能是：
- 棱镜 mod 的装备数据通常分散在多个 prefab 文件中（如 prefabs/ 目录下的各物品定义），而知识库收录的更多是核心机制代码。
- 护甲值（耐久）和减伤率（absorb_percent）是每个装备 prefab 中通过 inst.components.armor 单独设置的，没有集中在一个文件中。

如果你需要精确的装备名称和数值，建议直接查看棱镜 mod 的 scripts/prefabs/ 目录下对应装备的 prefab 文件，搜索 armor 和 absorb_percent 字段即可找到具体数值。

</details>

### 评价

能搜到具体内容，但全面程度（装备名称、id、尽可能多的相关机制）非常差，可以说不及格。

---

## 2. 棱镜 mod 的月光武器是怎么注册的？

**期望**：给出完整的注册流程和代码示例，涉及的函数（如 AddPrefabPostInit、RegisterPrefab 等）

<details>
<summary>📝 回答（点击展开）</summary>

从知识库中检索到的线索来看，棱镜 mod 中与月光武器相关的文件主要有：

1. 棱镜/scripts/recipes_legion.lua — 包含"重铸青光"等配方
2. 棱镜/scripts/prefabs/buffs_legion.lua — 包含"月光防御"等 buff
3. 棱镜/scripts/containers_legion.lua — 包含"月藏宝匣"、"月轮宝盘"、"月炆宝炊"等容器

虽然知识库没有直接给出完整的月光武器注册代码片段，但根据 DST Mod 开发的标准流程，棱镜 mod 的月光武器注册通常包含以下几个步骤：

1. **物品定义（Prefab 注册）**：在 scripts/prefabs/ 目录下，使用 Assets 和 Prefab 注册，添加 weapon 组件设置伤害和攻击范围，并添加月光阵营标签。

2. **配方注册（Recipe）**：在 recipes_legion.lua 中，使用 AddRecipe 或 AddRecipe2 注册制作配方，配置所需材料和科技等级。

3. **特殊机制（如"重铸青光"）**：可能是一种特殊的武器升级/重铸机制，通过自定义 crafting station（如"月藏宝匣"、"月轮宝盘"等容器）或自定义 action 来实现。

**（以下为补充知识）**

知识库没有完整收录棱镜月光武器的注册代码，可能原因有：月光武器相关代码分布在多个文件中，知识库只索引了部分文件；月光武器的具体名称可能使用了中文命名，导致检索时未命中。建议直接查看棱镜 mod 源码中的 scripts/prefabs/ 目录下的具体 prefab 文件，以及 scripts/recipes_legion.lua 中的配方注册代码。

</details>

### 评价

可能是切片策略和检索策略导致回答中“知识库没有直接给出完整的月光武器注册代码片段”，毕竟知识库来源是完整源代码切片，且除了无关的物品皮肤相关代码外无加密且注释全面。提升空间很大

---

## 3. 怎么制作一个可以随身携带的容器？

**期望**：给出完整的 prefab 代码、容器布局注册、配方注册步骤

<details>
<summary>📝 回答（点击展开）</summary>

好的，我已经收集到了足够的信息。下面为你详细讲解如何制作一个可以随身携带的容器（背包）。

---

## 制作随身携带容器的完整教程

### 核心思路

随身携带的容器 = **容器组件(container)** + **可装备组件(equippable)**。容器提供存储功能，装备组件让它可以穿戴在身上跟随玩家。

### 第一步：创建背包预制物

```lua
-- prefabs/mybackpack.lua

local assets = {
    Asset("ANIM", "anim/mybackpack.zip"),  -- 你的背包动画文件
}

local function onopen(inst)
    -- 打开时的效果（可选）
    inst.SoundEmitter:PlaySound("dontstarve/wilson/backpack_open")
end

local function onclose(inst)
    -- 关闭时的效果（可选）
    inst.SoundEmitter:PlaySound("dontstarve/wilson/backpack_close")
end

local function fn()
    local inst = CreateEntity()

    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddSoundEmitter()
    inst.entity:AddNetwork()

    MakeInventoryPhysics(inst)

    inst.AnimState:SetBank("mybackpack")
    inst.AnimState:SetBuild("mybackpack")
    inst.AnimState:PlayAnimation("idle")

    -- 1. 添加容器组件 —— 这是存储的核心
    inst:AddComponent("container")
    inst.components.container:WidgetSetup("mybackpack")  -- 使用自定义的格子布局
    inst.components.container.onopenfn = onopen
    inst.components.container.onclosefn = onclose

    -- 2. 添加可装备组件 —— 这是随身携带的关键
    inst:AddComponent("equippable")
    inst.components.equippable.equipslot = EQUIPSLOTS.BACK  -- 装备在背部

    -- 3. 添加检查组件
    inst:AddComponent("inspectable")

    -- 4. 添加掉落组件（死亡时掉落物品）
    inst:AddComponent("lootdropper")

    MakeHauntableLaunch(inst)

    return inst
end

return Prefab("mybackpack", fn, assets)
```

### 第二步：注册容器的格子布局

在 `modmain.lua` 或单独的 UI 文件中注册你的容器格子布局：

```lua
-- modmain.lua

-- 注册自定义容器的格子布局
local containers = require("containers")

-- 方式一：使用已有的布局（如普通背包）
-- inst.components.container:WidgetSetup("backpack")  -- 直接使用原版背包布局

-- 方式二：自定义布局
containers.MAXITEMSLOTS = 12  -- 确保最大格子数足够

containers.widgetsetup["mybackpack"] = {
    type = "pack",  -- 容器类型，pack 类型会跟随玩家
    widget = {
        slotpos = {},  -- 格子位置
        animbank = "ui_chest_3x3",  -- UI动画
        animbuild = "ui_chest_3x3",
        pos = Vector3(0, 200, 0),  -- UI位置偏移
    },
    issidewidget = true,  -- 侧边栏显示（背包类）
}

-- 生成格子位置（3行4列，共12格）
local slotpos = {}
for y = 0, 2 do
    for x = 0, 3 do
        table.insert(slotpos, Vector3(-75 + x * 50, -75 + y * 50, 0))
    end
end
containers.widgetsetup["mybackpack"].widget.slotpos = slotpos
```

### 第三步：添加制作配方

```lua
-- modmain.lua

local Recipe = require("defs/recipe")
local Ingredient = require("defs/ingredient")

AddRecipe("mybackpack", {
    Ingredient("cutstone", 4),
    Ingredient("silk", 6),
    Ingredient("rope", 2),
}, 
    RECIPETABS.SURVIVAL_TOOLS,  -- 生存工具栏
    TECH.NONE,  -- 无需科技
    "mybackpack",  -- 产物
    1,  -- 制作数量
    nil,  -- 皮肤
    nil,  -- 额外参数
    nil,  -- 制作音效
    nil,  -- 排序
    "images/inventoryimages/mybackpack.xml"  -- 图标
)
```

### 关键知识点说明

1. **`EQUIPSLOTS.BACK`**：装备在背部，这是最常见的随身容器位置。也可以使用 `EQUIPSLOTS.BODY`（身体）、`EQUIPSLOTS.HEAD`（头部）等。

2. **`type = "pack"`**：容器类型设为 `"pack"` 时，打开容器时不会阻挡玩家移动，且会跟随玩家。其他类型如 `"chest"` 是固定容器。

3. **`issidewidget = true`**：让容器界面显示在侧边，而不是屏幕中央，这是背包类容器的标准行为。

4. **格子布局**：`slotpos` 定义了每个格子的位置，`Vector3(x, y, z)` 中的 x 和 y 控制格子排列。

（以下为补充知识）

### 进阶功能

知识库中没有覆盖以下进阶内容，我为你补充：

**1. 限制只能放特定物品：**

```lua
inst.components.container.acceptfn = function(inst, item)
    -- 只允许放入食物
    return item.components.edible ~= nil
end
```

**2. 设置容器大小（格子数）：**

```lua
inst.components.container:WidgetSetup("mybackpack")  -- 在注册布局时定义格子数
-- 或者在代码中动态设置
inst.components.container:SetNumSlots(#slotpos)
```

**3. 无限堆叠（某些特殊背包）：**

```lua
inst.components.container:EnableInfiniteStackSize(true)
```

**4. 让容器在隐藏时保持打开状态（避免关闭音效问题）：**

```lua
inst.components.container.stay_open_on_hide = true
```

### 完整示例：一个简单的 6 格随身背包

```lua
-- prefabs/simplebag.lua
local assets = {
    Asset("ANIM", "anim/simplebag.zip"),
    Asset("ATLAS", "images/inventoryimages/simplebag.xml"),
}

local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)

    inst.AnimState:SetBank("simplebag")
    inst.AnimState:SetBuild("simplebag")
    inst.AnimState:PlayAnimation("idle")

    inst:AddComponent("container")
    inst.components.container:WidgetSetup("simplebag")

    inst:AddComponent("equippable")
    inst.components.equippable.equipslot = EQUIPSLOTS.BACK

    inst:AddComponent("inspectable")
    inst:AddComponent("lootdropper")

    return inst
end

return Prefab("simplebag", fn, assets)
```

```lua
-- modmain.lua
local containers = require("containers")

containers.MAXITEMSLOTS = 6
containers.widgetsetup["simplebag"] = {
    type = "pack",
    widget = {
        slotpos = {
            Vector3(0, 0, 0),
            Vector3(50, 0, 0),
            Vector3(0, -50, 0),
            Vector3(50, -50, 0),
            Vector3(0, -100, 0),
            Vector3(50, -100, 0),
        },
        animbank = "ui_chest_3x3",
        animbuild = "ui_chest_3x3",
        pos = Vector3(0, 200, 0),
    },
    issidewidget = true,
}

AddRecipe("simplebag", {
    Ingredient("cutstone", 2),
    Ingredient("silk", 4),
}, RECIPETABS.SURVIVAL_TOOLS, TECH.NONE)
```

这样你就拥有了一个可以穿戴在背上、随身携带的容器背包了！

</details>

### 评价

很详细全面，但似乎搞错了“可携带”和“可装备”的区别，能高分。

---

## 4. Beneath the World Below（深埋之下）mod 里有哪些自定义生物？

**期望**：列出 mod 中的生物名称、ID、基本特性

<details>
<summary>📝 回答（点击展开）</summary>

根据知识库中检索到的信息，我来整理一下 **Beneath the World Below（深埋之下）** mod 中的自定义生物内容。

## 深埋之下（Beneath the World Below）中的自定义生物

从知识库中检索到的信息，可以确认以下自定义生物/怪物相关内容：

### 1. **蠕虫 Boss（Worm Boss）**
- 来源：`wormstrings_en.lua` 文件中定义了 `WORMBOSSHOLE_EMERGE` 和 `WORMBOSSHOLE_WORM` 相关字符串
- 这是一种从地下钻出的巨型蠕虫 Boss，有独特的出场动画（地面震动、从地下冒出）
- 不同角色对其有不同台词，例如：
  - 普通角色："Something's coming up from below!"
  - WX-78："EARTH TREMORS INDICATE INFERIOR CREATURE MOVEMENT. PATHETICALLY OBVIOUS"
  - 薇克巴顿："There may be a dangerous creature below."

### 2. **潜伏阴影（Lurking Shadows）**
- 来源：`bwb_customizations.lua` 中的世界生成设置
- 归类在怪物（monsters）分组下
- 图标为 `ruinsshadow.tex`，与废墟阴影相关
- 可在洞穴世界生成设置中调节其生成频率

### 3. **寄生帽（Parasite Hat）**
- 来源：`bwb_customizations.lua` 中的世界生成设置
- 归类在怪物（monsters）分组下
- 图标为 `parasitehat.tex`
- 可在洞穴世界生成设置中调节其生成频率

### （以下为补充知识）

由于知识库中关于深埋之下 mod 的代码片段有限，我无法检索到该 mod 的完整生物列表。根据我对 DST Mod 社区的了解，**Beneath the World Below** 是一个大型洞穴扩展 mod，通常包含更多自定义生物，例如：

- **各种洞穴变异生物**（如洞穴蜘蛛变种、洞穴兔子变种等）
- **地下 Boss 系列**（除了蠕虫 Boss 外，可能还有其他地下首领）
- **环境生物**（与洞穴新生态环境相关的被动/中立生物）

**为什么知识库没有覆盖完整？** 知识库中只收录了该 mod 的部分配置文件（如世界生成设置和语言文件），而完整的生物 prefab 定义文件（如 `scripts/prefabs/` 目录下的文件）未被收录，因此无法获取完整的生物列表。

如果你需要完整的生物列表，建议直接查看该 mod 的 `scripts/prefabs/` 目录下的所有 `.lua` 文件，或者访问该 mod 的 Steam 创意工坊页面查看介绍。

</details>

### 评价

给出了3个还算详细的例子，虽然离全面还有一定距离。另外，如果问题是“深埋之下 mod 里有哪些自定义生物？”，rag认为知识库中没有该mod，说明中英文兼容非常必要，目前demo的嵌入和检索机制不能兼容。

---

## 5. DST 中食物的腐败速度怎么修改？

**期望**：给出完整 API 用法和代码示例

<details>
<summary>📝 回答（点击展开）</summary>

知识库中的信息比较零散，我来基于已有信息和你需要的答案进行整理。

## DST 食物腐败速度修改方法

### 核心机制

DST 中食物的腐败由 **`perishable` 组件**控制。每个食物预制体在定义时，会通过 `perishable` 组件设置腐败时间。

### 修改单个食物的腐败速度

在食物的 prefab 定义中，可以这样设置：

```lua
inst:AddComponent("perishable")
inst.components.perishable:SetPerishTime(TUNING.PERISH_FAST)  -- 设置腐败总时长（秒）
inst.components.perishable:StartPerishing()  -- 开始腐败计时
inst.components.perishable.onperishreplacement = "spoiled_food"  -- 腐败后变成腐烂食物
```

常用的 `TUNING` 预设值：
- `PERISH_FAST` — 快速腐败（如肉类、浆果）
- `PERISH_MED` — 中等速度
- `PERISH_SLOW` — 慢速腐败（如蜂蜜）
- `PERISH_PRESERVED` — 几乎不腐败

你也可以直接传入自定义秒数，例如 `TUNING.TOTAL_DAY_TIME * 6` 表示 6 天。

### 动态修改腐败速度

如知识库中[来源1：深埋之下]所示，可以通过**劫持 `ReducePercent` 方法**来控制腐败消耗：

```lua
-- 将腐败消耗屏蔽（食物永不腐败）
local _orig_ReducePercent = inst.components.perishable.ReducePercent
inst.components.perishable.ReducePercent = function(self, amount)
    if amount > 0 then return end  -- 屏蔽腐败消耗
    return _orig_ReducePercent(self, amount)
end
```

### 设置/获取腐败百分比

如知识库中[来源2：能力勋章]和[来源3：深埋之下]所示：

```lua
-- 设置新鲜度为 100%（食物回满）
inst.components.perishable:SetPercent(1)

-- 获取当前新鲜度
local percent = inst.components.perishable:GetPercent()

-- 同步新鲜度到另一个食物
newfood.components.perishable:SetPercent(oldfood.components.perishable:GetPercent())
```

### 全局修改所有食物的腐败速度

如果你想全局调整，可以在 modmain.lua 中遍历所有食物 prefab 的 `perishable` 组件，或者修改 `TUNING` 表中的常量（但注意 TUNING 是只读的，建议用 AddPrefabPostInit 方式）。

**示例：让所有肉类腐败速度减半**

```lua
AddPrefabPostInit("meat", function(inst)
    if inst.components.perishable then
        local orig = inst.components.perishable.SetPerishTime
        inst.components.perishable.SetPerishTime = function(self, time)
            return orig(self, time * 2)  -- 腐败时间翻倍 = 速度减半
        end
    end
end)
```

---

**（以下为补充知识）**

知识库中没有直接给出 `SetPerishTime` 的完整 API 文档和 `TUNING` 常量的具体数值表，这是因为知识库主要收录了各 Mod 的实际代码片段，而非官方 API 文档。如果你需要查看所有 `TUNING.PERISH_*` 常量的具体数值，可以查阅 DST 的 `tuning.lua` 文件，或直接在游戏中用控制台 `print(TUNING.PERISH_FAST)` 查看。

</details>

### 评价

比较丰富且详细，可以及格。希望原版代码入库后有兼顾原版和mod的更完整回答。
