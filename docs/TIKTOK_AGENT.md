# Agent nội dung TikTok — hướng dẫn nhanh

Một người vận hành một "studio thu nhỏ" cho kênh video ngắn không lộ mặt (faceless): Claude Code điều phối,
`vfactory` làm phần nặng. Mỗi bước trong bài viết gốc ứng với một lệnh có thật trong repo này:

| Bài viết | Ở đây |
|---|---|
| 1. Nghiên cứu chủ đề | skill `trend-research` (Reddit, HN, YouTube, GitHub, 30 ngày) + tìm web TikTok Creative Center → `ideas.md` |
| 2. Viết kịch bản | `short.json`: hook ≤ 3 giây, mỗi 2-4 giây một hình mới, nguồn cho mọi con số; `lint` chặn lỗi |
| 3. Hình ảnh, hoạt hình | emoji 3D Fluent (MIT) "diễn" ý tưởng, số đếm chạy đúng chữ, ảnh/clip của bạn với Ken Burns |
| 4. Dựng video tự động | Pillow + FFmpeg, 1080×1920, phụ đề karaoke, nhạc tự tổng hợp (không dính bản quyền), −14 LUFS |
| 5. Tối ưu đăng tải | `package`: ảnh bìa, caption, hashtag, bình luận ghim nguồn, checklist (nhãn nội dung AI) |
| 6. Phân tích hiệu quả | `metrics import` file CSV từ TikTok Studio → `insights` → `learnings.md` cho kịch bản sau |

## Cài đặt

```bash
pip install -e .[shorts]        # edge-tts: giọng Việt NamMinh / HoaiMy (cần internet)
# ffmpeg phải có trong PATH
```

## Dùng với Claude Code (khuyên dùng)

Mở Claude Code trong repo và nói tự nhiên:

- "Tạo kênh TikTok về lịch sử tài chính, handle @abc" → tạo `~/TikTokChannels/<tên>/channel.json`
- "Tìm 5 ý tưởng video tuần này cho kênh" → nghiên cứu xu hướng, ghi `ideas.md`
- "Làm video số 2 và 3, dừng lại cho tôi duyệt kịch bản" → `script.md` để duyệt
- "Duyệt, render bản final và chuẩn bị bài đăng" → MP4 + `publish/post.md`
- "Đây là file CSV từ TikTok Studio, video nào hiệu quả?" → `insights.md` + bài học cho video sau

Hoặc giao cả lô cho agent riêng: `tiktok-content-agent` (`.claude/agents/tiktok-content-agent.md`).

## Dùng bằng lệnh

```bash
C=~/TikTokChannels/bai-hoc-lich-su
python -m vfactory.shorts init $C --name "Bài học lịch sử" --niche "lịch sử & tâm lý tiền bạc" --handle @tenkenh
python -m vfactory.shorts new $C --title "Thiên tài Newton và bong bóng 1720"   # -> shorts/001-.../short.json
python -m vfactory.shorts lint $C/shorts/001-*/short.json                        # -> script.md
python -m vfactory.shorts build $C/shorts/001-*/short.json                       # bản nháp 540x960
python -m vfactory.shorts build $C/shorts/001-*/short.json --final               # 1080x1920
python -m vfactory.shorts package $C/shorts/001-*/short.json                     # ảnh bìa + caption + checklist
python -m vfactory.shorts log-post $C/shorts/001-*/short.json --url https://www.tiktok.com/@tenkenh/video/...
python -m vfactory.shorts metrics import $C ~/Downloads/tiktok_export.csv
python -m vfactory.shorts insights $C
python -m vfactory.shorts batch $C --final --only-new                            # render cả lô
```

Ví dụ hoàn chỉnh: `shorts/examples/001-newton-bong-bong/short.json` (≈ 54 giây, 12 cảnh, có nguồn).

## Giọng đọc

- `vi-VN-NamMinhNeural` / `vi-VN-HoaiMyNeural` qua edge-tts (văn bản được gửi tới dịch vụ TTS của Microsoft).
- Giọng của chính bạn: thêm `"audio": "takes/b03.m4a"` cho từng cảnh — thường hiệu quả nhất về độ tin cậy.
- `--voice none`: chỉ nhạc + chữ (dùng khi offline hoặc làm định dạng "text story").

## Nguyên tắc không thương lượng

- Không bịa số liệu, trích dẫn hay câu chuyện kiếm tiền; số ước tính phải được NÓI ra là ước tính.
- Không giả mạo khuôn mặt/giọng người thật; bật nhãn "Nội dung do AI tạo" khi đăng.
- Tài chính/sức khỏe: chỉ bài học, không khuyến nghị; có miễn trừ trách nhiệm.
- TikTok hạn chế nội dung trùng lặp, sản xuất hàng loạt thiếu nguyên bản: mỗi video cần nghiên cứu, hook và hình ảnh riêng.
- Agent không đăng bài hay đăng nhập tài khoản thay bạn: bạn bấm "Đăng".

Quy tắc nghề chi tiết: `.claude/skills/tiktok-shorts/references/tiktok-playbook.md`.
