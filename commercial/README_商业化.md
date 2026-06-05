# 商业化运营手册 —— 卖给高阳纺织厂的 SaaS 怎么跑

## 你卖的是什么

每个客户（纺织厂/布商/分销商）每个月交月费，你帮他们每天/每周自动产出一批
带他们自己声音、自己产品的数字人带货视频，发到抖音/快手。
他们不用懂技术，你跑流水线，他们看数据。

---

## 接一个新客户：5分钟开户

```bash
# 1. 新建租户
python -m commercial.tenant add --id factory_a --name "高阳A棉纺刘老板"

# 2. 打开并填写配置
nano commercial/tenants/factory_a/config.yaml
#   改：name / product / llm.api_key / digital_human.backend 等

# 3. 把客户声音参考录音放进去（可选）
cp 客户发来的录音.wav commercial/tenants/factory_a/voice_ref.wav

# 4. 把脚本放进去
mkdir -p commercial/tenants/factory_a/scripts
cp examples/towel_口播_可粘贴.txt commercial/tenants/factory_a/scripts/01_毛巾首条.txt
```

---

## 批量出片（每天的例行任务）

```bash
# 方式A：单租户跑一条
python batch.py --tenant factory_a --script commercial/tenants/factory_a/scripts/01_毛巾首条.txt

# 方式B：CSV 批量（多条脚本 / 多租户）
python batch.py --tenant factory_a --csv batch_input_example.csv

# 方式C：所有客户各出一条（自动读各自 scripts/ 目录最新脚本）
python batch.py --all-tenants --workers 3

# 查看队列状态
python batch.py --status
```

---

## 数字人后端怎么选

| 场景 | 后端 | 成本 | 效果 |
|------|------|------|------|
| 本地测试/无 GPU | `mock` | 0 | 字幕动画（无脸） |
| 正式出片·无 GPU | `guiji`（硅基智能） | ≈0.3元/分钟 | 真人数字人脸+口型 |
| 正式出片·有 GPU | `heygem`（自托管） | 一次性GPU成本 | 真人数字人脸+口型 |

### 切换到 guiji（硅基智能云端 API）

1. 注册 https://www.guiji.ai，微信/支付宝充值
2. 控制台选好数字人形象，记下 avatar_id
3. 租户配置里填：
   ```yaml
   digital_human:
     backend: guiji
     api_key: "你的硅基API Key"
     avatar_id: "选好的形象ID"
   ```

### 切换到 heygem（开源自托管，GPU服务器）

```bash
# 在 AutoDL 租一台 3090（约1元/小时），部署 HeyGem Docker
docker compose up -d   # 参考 https://github.com/GuijiAI/HeyGen

# 填写租户配置
digital_human:
  backend: heygem
  heygem_url: "http://<GPU服务器IP>:8080"
```

---

## 定价参考

| 套餐 | 内容 | 建议月费 |
|------|------|---------|
| 入门版 | 每月10条视频，字幕动画（无数字人脸），自动发布 | 299元/月 |
| 标准版 | 每月20条，硅基智能数字人脸，声音克隆 | 699元/月 |
| 旗舰版 | 每月30条+，自己GPU部署HeyGem，专属数字人形象 | 1499元/月 |

---

## 合规

- 声音克隆只能用客户本人授权的声音，签一份授权书
- 视频右下角自动加"AI生成内容"水印（Remotion已内置）
- 2025年9月起平台强制标识 AI 内容，发布时勾选
