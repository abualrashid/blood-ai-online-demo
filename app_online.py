import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


def simple_rule_based_analysis(labs):
    """
    نسخة مبسطة جدًا من المنطق:
    - تشخّص أنيميا نقص حديد من الـ CBC
    - تعطي لمحة عن الكلى / الكبد / السكري / القلب / العدوى حسب وجود البيانات
    """
    wbc  = labs.get("WBC")
    rbc  = labs.get("RBC")
    hgb  = labs.get("HGB")
    hct  = labs.get("HCT")
    mcv  = labs.get("MCV")
    mch  = labs.get("MCH")
    mchc = labs.get("MCHC")
    plt  = labs.get("PLT")

    creatinine = labs.get("Creatinine")
    urea       = labs.get("Urea")
    alt        = labs.get("ALT")
    ast        = labs.get("AST")
    alp        = labs.get("ALP")
    fasting_glucose = labs.get("FastingGlucose")

    results = {}

    # ===== CBC / Anemia =====
    results["hasCBC"] = hgb is not None or rbc is not None or mcv is not None

    anemia_types = []

    if hgb is not None:
        # عتبات تقريبية للبالغين
        if hgb < 13:
            # أنيميا + استخدام MCV لتحديد النوع
            if mcv is not None and mcv < 80:
                anemia_types.append("Likely iron deficiency (microcytic anemia)")
            elif mcv is not None and mcv > 100:
                anemia_types.append("Possible vitamin B12 / folate deficiency (macrocytic anemia)")
            else:
                anemia_types.append("Normocytic anemia (needs further evaluation)")
        else:
            anemia_types.append("No obvious anemia by Hb")

    results["AnemiaPrediction"] = anemia_types or ["Insufficient CBC data"]

    # ===== Kidney =====
    has_kidney_data = (creatinine is not None) or (urea is not None)
    results["hasKidney"] = has_kidney_data

    if has_kidney_data:
        if creatinine is not None and creatinine > 1.3:
            results["CKD_Prediction"] = "Possible impaired kidney function (high creatinine)"
        elif urea is not None and urea > 45:
            results["CKD_Prediction"] = "Possible impaired kidney function (high urea)"
        else:
            results["CKD_Prediction"] = "No clear evidence of CKD from current labs"
    else:
        results["CKD_Prediction"] = "No kidney labs provided"

    # ===== Liver =====
    has_liver_data = any(v is not None for v in [alt, ast, alp])
    results["hasLiver"] = has_liver_data

    if has_liver_data:
        if (alt is not None and alt > 40) or (ast is not None and ast > 40) or (alp is not None and alp > 130):
            results["Liver_Prediction"] = "Possible liver enzyme elevation (requires clinical correlation)"
        else:
            results["Liver_Prediction"] = "No clear liver enzyme abnormality"
    else:
        results["Liver_Prediction"] = "No liver enzymes provided"

    # ===== Diabetes =====
    results["hasDiabetes"] = fasting_glucose is not None
    if fasting_glucose is not None:
        if fasting_glucose >= 126:
            results["Diabetes_Prediction"] = "Fasting glucose in diabetic range"
        elif fasting_glucose >= 100:
            results["Diabetes_Prediction"] = "Impaired fasting glucose (pre-diabetes range)"
        else:
            results["Diabetes_Prediction"] = "Fasting glucose in normal range"
    else:
        results["Diabetes_Prediction"] = "No fasting glucose provided"

    # ===== Heart / Cardiovascular (مؤشر تقريبي جدًا) =====
    results["hasHeart"] = hdl is not None if (hdl := labs.get("HDL")) is not None else False
    # يمكن توسيعها لاحقًا بالكوليسترول، ضغط الدم، الخ…

    results["Heart_Prediction"] = "Not implemented in online demo version"

    # ===== Infection / Inflammation =====
    results["hasInfection"] = wbc is not None
    results["WBC_Value"] = wbc

    if wbc is None:
        results["Infection_Prediction"] = ["No WBC value provided"]
    else:
        if wbc > 11:
            results["Infection_Prediction"] = ["High WBC – may suggest acute infection or inflammation"]
        elif wbc < 4:
            results["Infection_Prediction"] = ["Low WBC – may suggest bone marrow suppression or viral illness"]
        else:
            results["Infection_Prediction"] = ["WBC within usual reference range"]

    return results


def build_reports(results, patient_info):
    name   = patient_info.get("Name", "غير مذكور")
    age    = patient_info.get("Age", "غير مذكور")
    gender = patient_info.get("Gender", "غير مذكور")
    now_str = datetime.now().strftime("%d-%m-%Y %H:%M")

    # تقرير عربي مبسط
    report_ar_lines = [
        "تقرير تحاليل دم (نسخة ديمو أونلاين)",
        "----------------------------------------",
        f"اسم المريض      : {name}",
        f"العمر           : {age}",
        f"الجنس           : {gender}",
        f"تاريخ التقرير   : {now_str}",
        "----------------------------------------",
        f"• حالة الدم/الأنيميا: {', '.join(results.get('AnemiaPrediction', []))}",
        f"• الكلى: {results.get('CKD_Prediction', '')}",
        f"• الكبد: {results.get('Liver_Prediction', '')}",
        f"• السكري: {results.get('Diabetes_Prediction', '')}",
        f"• مؤشر العدوى/الالتهاب: {results.get('Infection_Prediction', [''])[0]}",
        "----------------------------------------",
        "تنبيه: هذه النسخة أونلاين تعتمد على قواعد مبسطة في بايثون،",
        "وليست بنفس دقة النموذج الكامل المبني في MATLAB، ولا تغني عن مراجعة الطبيب."
    ]
    report_ar = "\n".join(report_ar_lines)

    # تقرير إنجليزي مبسط
    report_en_lines = [
        "Blood Test Report (Online Demo Version)",
        "----------------------------------------",
        f"Patient name    : {name}",
        f"Age             : {age}",
        f"Gender          : {gender}",
        f"Report date     : {now_str}",
        "----------------------------------------",
        f"Hematology / Anemia: {', '.join(results.get('AnemiaPrediction', []))}",
        f"Kidney status       : {results.get('CKD_Prediction', '')}",
        f"Liver status        : {results.get('Liver_Prediction', '')}",
        f"Diabetes risk       : {results.get('Diabetes_Prediction', '')}",
        f"Infection/Inflammation index: {results.get('Infection_Prediction', [''])[0]}",
        "----------------------------------------",
        "Disclaimer: This online demo uses simplified rule-based logic in Python.",
        "It is less accurate than the full MATLAB-based model and is not a medical diagnosis."
    ]
    report_en = "\n".join(report_en_lines)

    return report_ar, report_en


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True)

        patient_info = data.get("patientInfo", {})
        labs = data.get("labs", {})

        results = simple_rule_based_analysis(labs)
        reportAr, reportEn = build_reports(results, patient_info)

        return jsonify({
            "reportAr": reportAr,
            "reportEn": reportEn,
            "rawResults": results
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error (online demo)",
            "details": str(e)
        }), 500


@app.route("/", methods=["GET"])
def root():
    return "Online demo backend (Python-only rules). Use POST /analyze.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
