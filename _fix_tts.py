"""Fix TTS page - replace transcribeAudio and remove duplicate onAudioFileChange"""
p = r'D:/Code/Vs code/digital_human/third_party/LiveTalking/web/tts/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Remove the duplicate onAudioFileChange (keep only the first one)
# Find the second occurrence
first = c.find('function onAudioFileChange')
second = c.find('function onAudioFileChange', first + 10)
if second > 0:
    # Remove the second one
    end_of_second = c.find('\n            async function transcribeAudio', second)
    c = c[:second] + c[end_of_second:]

# Find and replace transcribeAudio
start = c.find('async function transcribeAudio()')
end = c.find('\n            async function uploadVoice()', start)

new_func = '''async function transcribeAudio() {
                const fileInput = document.getElementById("cloneAudioFile");
                const btnTranscribe = document.getElementById("btnTranscribe");
                if (!fileInput.files || fileInput.files.length === 0) {
                    showToast("请先选择音频文件", "error");
                    return;
                }
                const file = fileInput.files[0];
                btnTranscribe.disabled = true;
                showSpinner("正在识别语音...");
                try {
                    const form = new FormData();
                    form.append("file", file);
                    const r = await fetch("http://localhost:8011/asr", { method: "POST", body: form });
                    const d = await r.json();
                    if (d.text) {
                        document.getElementById("cloneRefText").value = d.text.trim();
                        showToast("识别完成", "success");
                    } else {
                        showToast("未识别到语音内容", "error");
                    }
                } catch (e) {
                    showToast("识别失败: " + e.message, "error");
                } finally {
                    btnTranscribe.disabled = false;
                    hideSpinner();
                }
            }
'''
c = c[:start] + new_func + c[end:]

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')
