# 第1步：下载对标视频

## 安装

```bash
pip install yt-dlp f2
```

## 使用

```bash
# 下载 YouTube 单条视频
python download.py --platform youtube --url "https://youtube.com/watch?v=xxx"

# 下载抖音账号最近20条（首次需配置 cookie）
python download.py --platform douyin --user "https://www.douyin.com/user/xxx" --limit 20
```

## 注意
- 下载是为了学习内容结构，仿写后发布自己原创的内容。禁止直接搬运原片上传。
- 抖音需要登录 cookie，参考 f2 文档：`f2 douyin --help`
