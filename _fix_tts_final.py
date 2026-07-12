"""Minimal TTS fix: only replace transcribeAudio and format hint"""
p = r'D:/Code/Vs code/digital_human/third_party/LiveTalking/web/tts/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Replace transcribeAudio
old_start = c.find('async function transcribeAudio()')
old_end = c.find('\n            async function uploadVoice()', old_start)
assert old_start > 0 and old_end > 0, f"Can't find function boundaries: {old_start}, {old_end}"

new_func = """async function transcribeAudio() {
                const fileInput = document.getElementById("cloneAudioFile");
                const btnTranscribe = document.getElementById("btnTranscribe");
                if (!fileInput.files || fileInput.files.length === 0) {
                    showToast('<i class="bi bi-exclamation-triangle me-1"></i>请先选择音频文件', 'error');
                    return;
                }
                const file = fileInput.files[0];
                btnTranscribe.disabled = true;
                showSpinner('正在通过 Whisper ASR 识别语音...');
                try {
                    const form = new FormData();
                    form.append("file", file);
                    const r = await fetch("http://localhost:8011/asr", { method: "POST", body: form });
                    const d = await r.json();
                    if (d.text) {
                        document.getElementById("cloneRefText").value = d.text.trim();
                        showToast('<i class="bi bi-check-circle me-1"></i>识别完成，请核对转录文本', 'success');
                    } else {
                        showToast('<i class="bi bi-info-circle me-1"></i>未识别到语音内容', 'info');
                    }
                } catch (e) {
                    showToast('<i class="bi bi-x-circle me-1"></i>识别失败: ' + e.message, 'error');
                } finally {
                    btnTranscribe.disabled = false;
                    hideSpinner();
                }
            }"""

c = c[:old_start] + new_func + c[old_end:]

# 2. Update format hint
c = c.replace(
    '支持 wav, mp3, flac, ogg, aac, webm, mp4（最大 10MB）',
    '支持 WAV、MP3、AAC、WebM、OGG 等浏览器音频格式（最大 10MB）'
)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print('OK -', len(c), 'bytes')
