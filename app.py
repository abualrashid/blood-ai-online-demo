import json
import subprocess
import tempfile
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # السماح للـ index.html بالاتصال

# المسار الكامل لبرنامج MATLAB المجمَّع
MATLAB_EXE = r"D:\IU\47\الترم الأول\Ai\مشاريع\final project\MATLAB\analyzeBlood_cli.exe"


def run_matlab_compiled(full_input_dict):
    """
    يشغّل analyzeBlood_cli.exe:
    - full_input_dict يجب أن يحتوي patientInfo و labs
    - يكتب JSON إلى ملف مؤقت
    - يشغّل exe
    - يقرأ JSON الناتج (results + reportAr + reportEn)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, "in.json")
        out_path = os.path.join(tmpdir, "out.json")

        # 1) كتابة المدخلات في JSON (نرسل الـ body كاملًا: patientInfo + labs)
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump(full_input_dict, f, ensure_ascii=False)

        # 2) استدعاء البرنامج المجمَّع
        subprocess.run(
            [MATLAB_EXE, in_path, out_path],
            check=True
        )

        # 3) قراءة النتائج الكاملة
        with open(out_path, "r", encoding="utf-8") as f:
            out_all = json.load(f)

    # out_all يحتوي: results, reportAr, reportEn
    return out_all


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True)

        # نتوقع أن JSON القادم من الواجهة يحتوي على:
        # {
        #   "patientInfo": {...},
        #   "labs": {...}
        # }
        # سنمرره كما هو إلى exe ليستخدمه MATLAB في
        # analyzeBlood + generateMedicalReport
        out_all = run_matlab_compiled(data)

        results = out_all.get("results", {})
        reportAr = out_all.get("reportAr", "")
        reportEn = out_all.get("reportEn", "")

        return jsonify({
            "reportAr": reportAr,
            "reportEn": reportEn,
            "rawResults": results
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "MATLAB compiled executable failed",
            "details": str(e)
        }), 500

    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route("/", methods=["GET"])
def root():
    return "Medical AI backend (compiled MATLAB) is running. Use POST /analyze.", 200


if __name__ == "__main__":
    # لا نحتاج MATLAB Engine الآن
    app.run(host="0.0.0.0", port=5000, debug=True)
