import json
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LOCAL_TZ = timezone(timedelta(hours=3))

def _is_valid_value(v):
    if v is None:
        return False
    try:
        v_float = float(v)
    except (TypeError, ValueError):
        return False
    return v_float > 0

def simple_rule_based_analysis(labs):
    wbc  = labs.get("WBC")
    rbc  = labs.get("RBC")
    hgb  = labs.get("HGB")
    hct  = labs.get("HCT")
    mcv  = labs.get("MCV")
    mch  = labs.get("MCH")
    mchc = labs.get("MCHC")
    plt  = labs.get("PLT")
    creatinine      = labs.get("Creatinine")
    urea            = labs.get("Urea")
    alt             = labs.get("ALT")
    ast             = labs.get("AST")
    alp             = labs.get("ALP")
    fasting_glucose = labs.get("FastingGlucose")
    hdl             = labs.get("HDL")

    # Ignore invalid (<=0) or missing
    wbc  = wbc  if _is_valid_value(wbc)  else None
    rbc  = rbc  if _is_valid_value(rbc)  else None
    hgb  = hgb  if _is_valid_value(hgb)  else None
    hct  = hct  if _is_valid_value(hct)  else None
    mcv  = mcv  if _is_valid_value(mcv)  else None
    mch  = mch  if _is_valid_value(mch)  else None
    mchc = mchc if _is_valid_value(mchc) else None
    plt  = plt  if _is_valid_value(plt)  else None
    creatinine      = creatinine      if _is_valid_value(creatinine)      else None
    urea            = urea            if _is_valid_value(urea)            else None
    alt             = alt             if _is_valid_value(alt)             else None
    ast             = ast             if _is_valid_value(ast)             else None
    alp             = alp             if _is_valid_value(alp)             else None
    fasting_glucose = fasting_glucose if _is_valid_value(fasting_glucose) else None
    hdl             = hdl             if _is_valid_value(hdl)             else None

    results = {}

    cbc_values = [wbc, rbc, hgb, hct, mcv, mch, mchc, plt]
    other_values = [creatinine, urea, alt, ast, alp, fasting_glucose, hdl]
    valid_cbc_count = sum(1 for v in cbc_values if v is not None)
    valid_other_count = sum(1 for v in other_values if v is not None)
    total_valid = valid_cbc_count + valid_other_count
    results["hasValidLabs"] = total_valid > 0

    if total_valid == 0:
        results["hasCBC"] = False
        results["hasKidney"] = False
        results["hasLiver"] = False
        results["hasDiabetes"] = False
        results["hasHeart"] = False
        results["hasInfection"] = False
        results["AnemiaPrediction"] = ["No lab data provided"]
        results["CKD_Prediction"] = "No lab data provided"
        results["Liver_Prediction"] = "No lab data provided"
        results["Diabetes_Prediction"] = "No lab data provided"
        results["Heart_Prediction"] = "No lab data provided"
        results["WBC_Value"] = None
        results["Infection_Prediction"] = ["No lab data provided"]
        return results

    # CBC / Anemia
    results["hasCBC"] = any(v is not None for v in [hgb, rbc, mcv])
    anemia_types = []
    if hgb is not None:
        if hgb < 13:
            if mcv is not None and mcv < 80:
                anemia_types.append("Likely iron deficiency (microcytic anemia)")
            elif mcv is not None and mcv > 100:
                anemia_types.append("Possible vitamin B12 / folate deficiency (macrocytic anemia)")
            else:
                anemia_types.append("Normocytic anemia (needs further evaluation)")
        else:
            anemia_types.append("No obvious anemia by Hb")
    else:
        anemia_types.append("Insufficient data for anemia assessment")
    results["AnemiaPrediction"] = anemia_types or ["Insufficient CBC data"]

    # Kidney
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

    # Liver
    has_liver_data = any(v is not None for v in [alt, ast, alp])
    results["hasLiver"] = has_liver_data
    if has_liver_data:
        if (alt is not None and alt > 40) or (ast is not None and ast > 40) or (alp is not None and alp > 130):
            results["Liver_Prediction"] = "Possible liver enzyme elevation (requires clinical correlation)"
        else:
            results["Liver_Prediction"] = "No clear liver enzyme abnormality"
    else:
        results["Liver_Prediction"] = "No liver enzymes provided"

    # Diabetes
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

    # Heart (simplified)
    results["hasHeart"] = hdl is not None
    results["Heart_Prediction"] = "Not implemented in online demo version"

    # Infection / Inflammation
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
    name   = patient_info.get("Name") or patient_info.get("FullName") or "غير مذكور"
    age    = patient_info.get("Age", "غير مذكور")
    gender = patient_info.get("Gender", "غير مذكور")
    now = datetime.now(LOCAL_TZ)
    now_str = now.strftime("%d-%m-%Y %H:%M")
    has_valid_labs = results.get("hasValidLabs", False)

    scientific_note_ar = (
        "• لاحظت أبحاث حديثة (Biomedicines 2022, PMC9687310) أن بعض مؤشرات العد الدموي الشامل "
        "(مثل ارتفاع WBC أو RDW أو NLR أو زيادة PLT) قد ترتبط بزيادة خطر أمراض القلب والشرايين "
        "والسكري من النوع الثاني. هذا فقط مؤشر استرشادي ولابد من تقييم سريري شامل."
    )
    scientific_note_en = (
        "• Recent studies (Biomedicines 2022, PMC9687310) have shown that elevated CBC indices "
        "(like high WBC, RDW, NLR, or increased PLT) may be associated with a higher long-term risk of "
        "cardiovascular disease and type 2 diabetes. This is only a warning marker, not a clinical diagnosis."
    )

    if not has_valid_labs:
        msg_ar = "لم يتم إدخال أي قيم مخبرية صالحة. يرجى إدخال نتائج التحاليل الفعلية قبل استخدام هذه الأداة."
        msg_en = "No valid lab values were provided. Please enter actual lab results before using this online demo."
        report_ar_lines = [
            "تقرير تحاليل دم (نسخة ديمو أونلاين)",
            "----------------------------------------",
            f"اسم المريض      : {name}",
            f"العمر           : {age}",
            f"الجنس           : {gender}",
            f"تاريخ التقرير   : {now_str}",
            "----------------------------------------",
            msg_ar,
            "----------------------------------------",
            "تنبيه: هذه النسخة أونلاين تعتمد على قواعد مبسطة في بايثون،",
            "وليست بنفس دقة النموذج الكامل المبني في MATLAB، ولا تغني عن مراجعة الطبيب."
        ]
        report_en_lines = [
            "Blood Test Report (Online Demo Version)",
            "----------------------------------------",
            f"Patient name    : {name}",
            f"Age             : {age}",
            f"Gender          : {gender}",
            f"Report date     : {now_str}",
            "----------------------------------------",
            msg_en,
            "----------------------------------------",
            "Disclaimer: This online demo uses simplified rule-based logic in Python.",
            "It is less accurate than the full MATLAB-based model and is not a medical diagnosis."
        ]
        return "\n".join(report_ar_lines), "\n".join(report_en_lines)

    report_ar_lines = [
        "تقرير تحاليل دم (نسخة ديمو أونلاين)",
        "----------------------------------------",
        f"اسم المريض      : {name}",
        f"العمر           : {age}",
        f"الجنس           : {gender}",
        f"تاريخ التقرير   : {now_str}",
        "----------------------------------------",
        f"• حالة الدم/الأنيميا: {', '.join(results.get('AnemiaPrediction', []))}"
    ]

    if results.get('hasKidney'):
        report_ar_lines.append(f"• الكلى: {results.get('CKD_Prediction', '')}")
    if results.get('hasLiver'):
        report_ar_lines.append(f"• الكبد: {results.get('Liver_Prediction', '')}")
    if results.get('hasDiabetes'):
        report_ar_lines.append(f"• السكري: {results.get('Diabetes_Prediction', '')}")

    report_ar_lines.append(
        f"• مؤشر العدوى/الالتهاب: {results.get('Infection_Prediction', [''])[0]}"
    )
    if results.get("hasCBC"):
        report_ar_lines.append(scientific_note_ar)

    report_ar_lines += [
        "----------------------------------------",
        "تنبيه: هذه النسخة أونلاين تعتمد على قواعد مبسطة في بايثون،",
        "وليست بنفس دقة النموذج الكامل المبني في MATLAB، ولا تغني عن مراجعة الطبيب."
    ]

    report_en_lines = [
        "Blood Test Report (Online Demo Version)",
        "----------------------------------------",
        f"Patient name    : {name}",
        f"Age             : {age}",
        f"Gender          : {gender}",
        f"Report date     : {now_str}",
        "----------------------------------------",
        f"Hematology / Anemia: {', '.join(results.get('AnemiaPrediction', []))}"
    ]
    if results.get('hasKidney'):
        report_en_lines.append(
            f"Kidney status       : {results.get('CKD_Prediction', '')}"
        )
    if results.get('hasLiver'):
        report_en_lines.append(
            f"Liver status        : {results.get('Liver_Prediction', '')}"
        )
    if results.get('hasDiabetes'):
        report_en_lines.append(
            f"Diabetes risk       : {results.get('Diabetes_Prediction', '')}"
        )

    report_en_lines.append(
        f"Infection/Inflammation index: {results.get('Infection_Prediction', [''])[0]}"
    )

    if results.get("hasCBC"):
        report_en_lines.append(scientific_note_en)
    report_en_lines += [
        "----------------------------------------",
        "Disclaimer: This online demo uses simplified rule-based logic in Python.",
        "It is less accurate than the full MATLAB-based model and is not a medical diagnosis."
    ]
    report_ar = "\n".join(report_ar_lines)
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
