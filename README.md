<a href="https://github.com/3899/eSIM-SMS-Forwarder">
  <img src="https://socialify.git.ci/3899/eSIM-SMS-Forwarder/image?description=1&descriptionEditable=%E9%80%82%E7%94%A8%E4%BA%8E%20eSIM%20%2F%20SMS%20%E7%9A%84%E5%BC%80%E6%BA%90%E7%9F%AD%E4%BF%A1%E6%8E%A5%E6%94%B6%E4%B8%8E%E8%BD%AC%E5%8F%91%E5%B7%A5%E5%85%B7%E3%80%82&font=Source%20Code%20Pro&logo=https%3A%2F%2Fgithub.com%2F3899%2FeSIM-SMS-Forwarder%2Fblob%2Fmain%2Ffrontend%2Fpublic%2Fapp-icon.png%3Fraw%3Dtrue&name=1&owner=1&pattern=Floating%20Cogs&theme=Auto" alt="eSIM-SMS-Forwarder" />
</a>

<div align="center">
  <br/>

  <div>
    <a href="./LICENSE">
      <img
        src="https://img.shields.io/github/license/3899/eSIM-SMS-Forwarder?style=flat-square"
      />
    </a >
    <a href="https://github.com/3899/eSIM-SMS-Forwarder/releases">
      <img
        src="https://img.shields.io/github/v/release/3899/eSIM-SMS-Forwarder?style=flat-square"
      />
    </a >
    <a href="https://github.com/3899/eSIM-SMS-Forwarder/releases">
      <img
        src="https://img.shields.io/github/downloads/3899/eSIM-SMS-Forwarder/total?style=flat-square"
      />  
    </a >
  </div>

  <br/>

  <picture>
    <img src="./static/Web_Console.png" width="100%" alt="Web_Console" />
  </picture>
  
</div>

# eSIM SMS Forwarder

一个运行在 Debian 设备上的轻量服务，用来做 eSIM 管理、短信接收、Apprise 多渠道转发，以及浏览器里的可视化控制台。

项目目标很直接：

- 在支持 eUICC 的设备上切换内置 eSIM Profile
- 接收短信并转发到 Apprise 与原生企业应用通道
- 提供低负载、可实时反馈执行进度的 Web 管理页面
- 兼容普通 SIM 场景，只启用短信转发，不安装 `lpac`

## 功能描述

### eSIM 管理

- 读取 eUICC 内置 Profiles
- 一键切换当前启用的 eSIM Profile
- 切卡后自动执行基带恢复，帮助重新注册网络
- 支持为 Profile 关联短信中心，切卡后自动恢复对应 SMSC
- 支持按 cron 表达式执行保活任务，自动切换指定 Profile、发送短信并回切原 Profile
- Web 页面显示执行进度和 Shell 日志

### 短信转发

- 通过 `ModemManager` 读取短信
- 自动转发新短信到 Bark、Telegram、Email、PushPlus、Server酱、企业微信群机器人、飞书机器人、钉钉群机器人、Webhook Lite 以及企业应用类通道
- 自动处理中文转义内容
- 自动尝试解码 Base64 短信正文
- 支持在页面里查看最近短信
- 支持在保活任务里按当前号码与短信内容测试发送
- 支持“重发最后一条短信”

### 设备控制

- 查看运营商、注册状态、信号强度、接入制式
- 重启基带
- 重启短信转发服务
- 配置 APN、网络制式、手动选网
- 维护保活任务、切卡缓冲时间、执行队列与最近记录
- 在高级设置里维护通知渠道

### Web 控制台

- React + shadcn/ui 动态前端
- 点击任意操作后立即进入任务态
- Shell 面板实时显示执行步骤
- 前后端由同一个 Python 服务托管
- 普通 SIM 模式下自动禁用 eSIM 相关功能

## 技术栈

### 设备侧

- Debian
- Python 3
- systemd
- ModemManager / `mmcli`
- libqmi / `qmicli`
- NetworkManager / `nmcli`
- `lpac`

### 前端

- React 19
- TypeScript
- Vite
- Tailwind CSS v4
- shadcn/ui
- sonner
- lucide-react

## 安装说明

### 1. 一键安装

默认安装模式为 eSIM 模式：

```bash
curl -fsSL https://ghproxy.net/https://raw.githubusercontent.com/3899/eSIM-SMS-Forwarder/main/scripts/install_latest.sh | sudo sh
```

如果设备使用普通 SIM，只需要短信转发，不需要 `lpac` 和 eSIM 管理：

```bash
curl -fsSL https://ghproxy.net/https://raw.githubusercontent.com/3899/eSIM-SMS-Forwarder/main/scripts/install_latest.sh | sudo sh -s -- --sim-type physical
```

安装脚本会自动：

- 检查系统环境、架构、systemd 和基础依赖
- 下载最新 Release，失败时回退到 `main` 分支源码包
- 安装常用依赖：`python3`、`curl`、`unzip`、`modemmanager`、`network-manager`、`libqmi-utils`
- 在 `aarch64 / arm64` 的 eSIM 模式下自动安装内置 `lpac`
- 安装并启用 Web 管理服务与短信转发服务
- 输出访问地址、服务状态和通知渠道摘要

### 2. 安装模式

#### eSIM 模式

- 参数：`--sim-type esim`
- 默认模式
- 安装 `lpac`
- 启用 eSIM 卡切换能力
- Web 前端显示 eSIM Profiles 和切卡按钮

#### 普通 SIM 模式

- 参数：`--sim-type physical`
- 不安装 `lpac`
- 删除 `lpac-switch` 包装脚本
- 后端禁用 eSIM Profile 读取与切卡接口
- Web 前端自动隐藏/禁用 eSIM 相关操作

安装完成后会写入：

```text
/etc/esim-sms-forwarder.conf
```

示例内容：

```ini
SIM_TYPE=physical
ESIM_MANAGEMENT_ENABLED=0
FOURG_WIFI_ADMIN_HOST=auto
FOURG_WIFI_ADMIN_PORT=8080
```

### 3. 手动部署

```bash
git clone https://github.com/3899/eSIM-SMS-Forwarder.git
cd eSIM-SMS-Forwarder
sudo sh ./deploy/install.sh
```

普通 SIM 模式：

```bash
sudo sh ./deploy/install.sh --sim-type physical
```

## 使用说明

### 快速使用指南

推荐按下面的顺序开始使用，先把基础链路跑通，再逐步启用高级能力。

1. 安装完成后，先确认两个服务状态正常：

```bash
systemctl status 4g-wifi-admin.service
systemctl status sms-forwarder.service
```

2. 通过浏览器打开管理页面：

```text
IPv4: http://<device-ipv4>:8080/
IPv6: http://[<device-ipv6>]:8080/
```

3. 登录页面后先看首页状态卡片，确认以下信息是否正常：

- 基带在线
- 运营商、信号、注册状态正常
- 最近短信列表可刷新
- Web 管理服务和短信转发服务状态正常

4. 先完成一条通知渠道配置，再验证发送链路：

- 进入“高级设置”里的通知渠道区域
- 新增一个最容易验证的通道，例如 Bark、Telegram 或 Email
- 保存后用“重发最后一条短信”或保活任务里的“测试短信”验证

5. 如果是 eSIM 设备，再继续配置 eSIM 相关能力：

- 检查 Profiles 列表能否正常加载
- 为常用 Profile 配置短信中心
- 手动切换一次 Profile，确认切卡、基带恢复和网络重新注册流程正常

6. 最后再启用自动化能力：

- 配置 APN、网络制式、选网策略
- 创建保活任务
- 用手动执行先验证一轮，再交给 cron 定时运行

推荐的首次验收顺序：

1. 页面能打开
2. 状态能刷新
3. 最近短信能读取
4. 通知能发出去
5. 测试短信能发送
6. eSIM 切卡成功
7. 保活任务手动执行成功
8. 保活任务定时执行成功

常见使用建议：

- 第一次配置时先只启用一个通知通道，问题更容易定位
- 第一次切卡前先记录当前可用网络和当前 Profile，便于回滚
- 保活任务先手动跑通，再启用定时，避免定时任务带着错误参数持续失败
- 如果设备要通过公网域名访问，建议放到反向代理和 HTTPS 后面，不建议直接裸露 `8080`

### 通知渠道配置

实际配置文件路径：

```text
/etc/sms-forwarder.conf
```

至少需要填写：

```ini
MODEM_ID=any
NOTIFICATION_TARGETS_JSON=[{"id":"bark-primary","label":"Bark","url":"barks://bark.example.com/device_key?group=sms&level=active","enabled":true},{"id":"email-primary","label":"Email","url":"mailtos://user:password@smtp.example.com:465?from=sender%40example.com&to=receiver%40example.com","enabled":false}]
FORWARD_SMS_STATES=received
```

`NOTIFICATION_TARGETS_JSON` 以 URL 形式保存通知目标。

- Apprise 通道示例：`barks://...`、`tgram://...`、`mailtos://...`、`pushplus://...`、`schan://...`
- 原生通道示例：`webhooklite://config?...`、`wecomapp://config?...`、`feishuapp://config?...`、`dingtalkcorp://config?...`

### 通知渠道使用指南

推荐直接在 Web 控制台里维护通知渠道，通常不需要手改 `/etc/sms-forwarder.conf`。

基本操作步骤：

1. 打开 Web 控制台，进入“高级设置”里的通知渠道区域。
2. 点击新增通道，选择需要的通知类型。
3. 按表单填写参数并启用该通道。
4. 保存配置，页面会把结构化表单转换成 `NOTIFICATION_TARGETS_JSON`。
5. 通过“重发最后一条短信”或保活任务里的测试发送，验证链路是否正常。

通用规则：

- 当前前端约束为“每种通道只保留一条配置”。
- 关闭“启用”开关后，该通道会保留配置但不会参与发送。
- 保存通知配置后，Web 后端会重载短信转发服务。
- 同一次发送中，如果部分通道失败，其他成功通道仍会继续发送。

各通道填写说明：

- `Email`
  - 填写 SMTP 服务器、端口、用户名、密码、发件人、收件人。
  - `465` 通常对应 SSL，`587` 常见于 STARTTLS；如果服务商要求明文端口，请按实际文档填写。
  - 收件人支持多个，前端会按逗号拆分。
- `PushPlus`
  - 只需要填写 Token。
- `Server酱`
  - 填写 SendKey。
- `企业微信群机器人`
  - 填写机器人 Webhook URL 中的 `key`。
- `飞书机器人`
  - 填写机器人 Token；如果你拿到的是完整 Webhook URL，取最后一段 token 即可。
- `钉钉群机器人`
  - 必填 Access Token。
  - 如果机器人启用了加签，再填写 Secret。
  - 如果需要 @ 指定手机号，可填写多个手机号，逗号分隔。
- `Webhook Lite`
  - 适合把短信内容转发给自建 HTTP 服务。
  - 目前支持 `GET`、`POST form`、`POST json`、`POST text`。
  - `Title Key` 和 `Body Key` 用来指定标题和正文的字段名；留空时使用默认值。
  - 当前版本不支持自定义请求头、签名、`PUT/PATCH` 和复杂模板。
- `企业微信应用`
  - 填写 `Corp ID`、`Agent ID`、`Secret`。
  - 接收者可选成员、部门、标签，支持多个，逗号分隔。
  - 如果三类接收者都不填，企业微信接口通常会拒绝发送。
- `飞书企业应用`
  - 填写 `App ID`、`App Secret`。
  - 填写接收者 ID，并选择对应的 `receive_id_type`，例如 `open_id`、`user_id`、`chat_id`。
- `钉钉企业内机器人`
  - 填写企业机器人 Webhook 地址。
  - 如果启用了加签，再填写 Secret。
  - 当前实现发送文本消息，适合内部告警和短信转发提醒。

建议的验证顺序：

1. 先只启用一个通道，确认参数无误。
2. 使用“重发最后一条短信”验证基础发送链路。
3. 再逐步增加其他通道，避免多个目标同时出错时难以定位。
4. 如果是企业应用类通道，优先检查 token、接收者 ID 和平台侧权限范围。

常见排查思路：

- 页面保存成功但没有收到通知：先检查通道是否处于启用状态，再看 `journalctl -u sms-forwarder.service -f`。
- 企业应用类接口报鉴权失败：优先核对 `Corp ID/App ID`、密钥、机器人或应用权限。
- Webhook 收不到字段：确认请求方法和编码格式是否与你的服务端一致。
- 邮件发不出去：优先检查 SMTP 端口、加密方式和服务商是否要求授权码而不是登录密码。

### 服务管理

```bash
systemctl status 4g-wifi-admin.service
systemctl status sms-forwarder.service
```

```bash
journalctl -u 4g-wifi-admin.service -f
journalctl -u sms-forwarder.service -f
```

### Web 页面

默认监听策略：

- 默认使用自动双栈监听，优先尝试同时支持 IPv4 / IPv6
- 若当前系统不支持 IPv6，则自动回退到 IPv4
- 显式设置 `FOURG_WIFI_ADMIN_HOST=0.0.0.0` 时只监听 IPv4
- 显式设置 `FOURG_WIFI_ADMIN_HOST=::` 时优先监听 IPv6 双栈

默认访问格式：

```text
IPv4: http://<device-ipv4>:8080/
IPv6: http://[<device-ipv6>]:8080/
```

如果域名的 `AAAA` 记录指向设备的 IPv6 地址，且对应端口已放通，也可以直接通过域名访问：

```text
http://panel.example.com:8080/
```

常用监听配置示例：

```ini
# 自动双栈，失败回退 IPv4（默认）
FOURG_WIFI_ADMIN_HOST=auto
FOURG_WIFI_ADMIN_PORT=8080

# 只监听 IPv4
FOURG_WIFI_ADMIN_HOST=0.0.0.0

# 只监听本机 IPv6
FOURG_WIFI_ADMIN_HOST=::1
```

说明：

- 域名通过 `AAAA` 记录访问时，不需要写 IPv6 方括号
- 如果要公网暴露，仍建议放在反向代理和 HTTPS 后面，本项目本次不内置 nginx/caddy

页面内可完成：

- 查看当前号码、运营商、信号和服务状态
- 查看最近短信
- 为 Profile 配置并应用短信中心，切卡后自动恢复
- 重发最后一条短信
- 重启基带
- 配置保活任务，按时自动切卡、发短信、通知并切回原 Profile
- 在保活任务里测试当前短信配置，确认发送链路
- 修改通知渠道配置
- 修改 APN、网络制式和选网策略
- 在 eSIM 模式下切换 Profile

## 构建说明

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 前端构建

```bash
cd frontend
npm run lint
npm run build
```

### Python 检查

```bash
python -m py_compile deploy/web_admin/4g_wifi_admin.py
python -m py_compile deploy/sms_forwarder/sms_forwarder.py
python -m unittest discover -s tests -p "test_*.py"
```

## 目录结构

```text
deploy/
  esim/
    lpac-switch.sh
    lpac
  sms_forwarder/
    sms_forwarder.py
    sms-forwarder.service
    sms-forwarder.conf.example
  web_admin/
    4g_wifi_admin.py
    4g-wifi-admin.service
    frontend_dist/

frontend/
  src/
```

## 说明

这个项目优先解决的是“稳定可用”，而不是“大而全”。重点是：

- 切卡动作有明确反馈
- 短信链路可追踪
- 低内存设备也能长期运行
- 页面操作有实时响应

如果你只需要保号收短信，推荐普通 SIM 模式；如果你需要切换 eSIM Profile，再使用默认 eSIM 模式即可。
