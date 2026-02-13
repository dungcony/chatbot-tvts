"""
Chatbot Tu van Tuyen sinh - Flask Backend
Truong + keywords doc tu MongoDB (collection: schools).
"""
import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template
from services import vector_search, generate_answer
from models.chat_history import get_collection as get_chat_collection, get_recent_history

app = Flask(__name__)
GREETING_KEYWORDS = {"xin chao", "hello", "hi", "chao", "hey", "chao ban", "alo"}
CONFIRM_KEYWORDS = {"co", "ban co", "co ban", "dung", "dung roi", "ok", "yes", "vang",
                     "uh", "uhm", "muon", "toi muon", "minh muon", "dong y", "duoc", "được"}


def is_greeting(query):
    return query.lower().strip().rstrip("!.") in GREETING_KEYWORDS


def is_confirmation(query):
    return query.lower().strip().rstrip("!.") in CONFIRM_KEYWORDS


def detect_school_from_history(session_id):
    """Tim school da duoc detect trong lich su hoi thoai gan nhat."""
    from models.school import detect_school
    history = get_recent_history(session_id, limit=10)
    for msg in reversed(history):
        school = detect_school(msg["message"])
        if school:
            return school
    return None


def save_chat(session_id, role, message):
    get_chat_collection().insert_one({
        "session_id": session_id, "role": role, "message": message,
        "timestamp": datetime.now(timezone.utc)
    })


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    if not query:
        return jsonify({"error": "Vui long nhap cau hoi"}), 400

    try:
        save_chat(session_id, "user", query)

        if is_greeting(query):
            from models.school import get_all_schools
            schools = get_all_schools()
            lst = "\n".join([f"* **{s['name']}**" for s in schools])
            answer = f"Xin chao! Toi la tro ly tu van tuyen sinh.\n\n{lst}\n\nBan muon tim hieu ve truong nao?"
            save_chat(session_id, "bot", answer)
            return jsonify({"answer": answer, "sources": []})

        from models.school import detect_school, get_all_schools
        school = detect_school(query)

        # Neu khong detect duoc truong tu query hien tai,
        # thu tim tu lich su hoi thoai (user da chon truong truoc do)
        if not school:
            school = detect_school_from_history(session_id)

        # Neu van khong tim thay truong nao
        if not school:
            schools = get_all_schools()
            lst = "\n".join([f"* **{s['name']}**" for s in schools])
            answer = f"Ban muon hoi thong tin cua truong nao?\n\n{lst}\n\nHay cho toi biet nhe!"
            save_chat(session_id, "bot", answer)
            return jsonify({"answer": answer, "sources": []})

        # Lay lich su hoi thoai de truyen vao LLM
        history = get_recent_history(session_id, limit=6)

        # Neu query qua ngan (vd: chi la ten truong hoac xac nhan),
        # bo sung context tu lich su
        effective_query = query
        if len(query.split()) <= 3 or is_confirmation(query):
            # Gop cac cau hoi cua user tu lich su de lam query search tot hon
            user_msgs = [m["message"] for m in history if m["role"] == "user"]
            if user_msgs:
                effective_query = " ".join(user_msgs[-3:])  # 3 tin nhan gan nhat

        context_docs = vector_search(effective_query, school=school, num_candidates=150, limit=4)
        if not context_docs:
            return jsonify({"answer": "Xin loi, khong tim thay thong tin lien quan.", "sources": []})

        answer = generate_answer(query, context_docs, history=history)
        save_chat(session_id, "bot", answer)
        sources = [{"content": d["content"][:200], "score": round(d.get("score", 0), 4)} for d in context_docs]
        return jsonify({"answer": answer, "sources": sources})
    except Exception as e:
        return jsonify({"error": f"Loi: {str(e)}"}), 500


# ==================== ADMIN ====================

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/admin/api/schools", methods=["GET"])
def api_schools():
    from models.school import get_all_schools
    return jsonify({"schools": get_all_schools()})

@app.route("/admin/api/schools", methods=["POST"])
def api_add_school():
    d = request.get_json()
    sid = d.get("school_id", "").strip().lower()
    name = d.get("name", "").strip()
    kws = [k.strip().lower() for k in d.get("keywords", []) if k.strip()]
    if not sid or not name or not kws:
        return jsonify({"error": "Thieu thong tin"}), 400
    from models.school import add_school
    add_school(sid, name, kws)
    return jsonify({"success": True})

@app.route("/admin/api/schools/delete", methods=["POST"])
def api_del_school():
    from models.school import remove_school
    remove_school(request.get_json().get("school_id", ""))
    return jsonify({"success": True})

@app.route("/admin/api/add-urls", methods=["POST"])
def api_add_urls():
    d = request.get_json()
    sid = d.get("school_id", "")
    urls = [u.strip() for u in d.get("urls", []) if u.strip()]
    if not sid or not urls:
        return jsonify({"error": "Thieu thong tin"}), 400
    from models.school import add_urls
    add_urls(sid, urls)
    return jsonify({"success": True, "count": len(urls)})

@app.route("/admin/api/delete-url", methods=["POST"])
def api_del_url():
    d = request.get_json()
    sid = d.get("school_id", "")
    url = d.get("url", "")
    if not sid or not url:
        return jsonify({"error": "Thieu thong tin"}), 400
    from models.school import remove_url
    remove_url(sid, url)
    return jsonify({"success": True})

@app.route("/admin/api/crawl-url", methods=["POST"])
def api_crawl_url():
    """Crawl 1 URL don le."""
    d = request.get_json()
    sid = d.get("school_id", "")
    url = d.get("url", "")
    if not sid or not url:
        return jsonify({"error": "Thieu thong tin"}), 400
    from scripts.crawl_data import crawl_single
    return jsonify(crawl_single(sid, url))

@app.route("/admin/api/data-files", methods=["GET"])
def api_data_files():
    from scripts.prepare_data import get_all_data_files
    return jsonify({"files": get_all_data_files()})

@app.route("/admin/api/crawl", methods=["POST"])
def api_crawl():
    sid = (request.get_json() or {}).get("school_id", None)
    from scripts.crawl_data import crawl_school
    return jsonify(crawl_school(sid))

@app.route("/admin/api/embed", methods=["POST"])
def api_embed():
    from scripts.prepare_data import process_files
    return jsonify(process_files())


if __name__ == "__main__":
    print("=" * 50)
    print("Chatbot Tu van Tuyen sinh")
    print("http://localhost:5000")
    print("http://localhost:5000/admin")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
