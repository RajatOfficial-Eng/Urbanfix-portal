from reportlab.graphics.barcode import qr, code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from flask import redirect, render_template, request
from flask import session
from flask import session, redirect
from flask import session, flash, request, redirect, render_template
from openpyxl import Workbook

# ==================================================
# FLASK CONFIGURATION
# ==================================================
app = Flask(
    __name__,
    template_folder="template",   # your folder name
    static_folder="style",
    instance_relative_config=False
)
app.secret_key = "urbanfix_secret_key"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
os.makedirs(DATABASE_FOLDER, exist_ok=True)

DATABASE_PATH = os.path.join(DATABASE_FOLDER, "urbanfix.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
# ==================================================
# DATABASE MODEL
# ==================================================
class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    complaint_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    mobile = db.Column(db.String(15))

    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    area = db.Column(db.String(100))

    complaint_type = db.Column(db.String(20))   # ✅ ADD THIS
    priority = db.Column(db.String(10))         # ✅ ALREADY ADDED

    assigned_department = db.Column(db.String(100))

    status = db.Column(db.String(30), default="Registered")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    in_progress_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)

# =========================
# USER MODEL (FOR LOGIN)
# =========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    mobile = db.Column(db.String(15))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default="Citizen")

# =========================
# DEPARTMENT MODEL
# =========================
class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), unique=True)
    head_officer = db.Column(db.String(100))
    email = db.Column(db.String(100))
    status = db.Column(db.String(20), default="Active")




def get_priority(category):
    if category in ["water", "fire", "electricity"]:
        return "critical"
    elif category in ["road", "traffic"]:
        return "high"
    elif category in ["garbage", "pollution"]:
        return "Medium"
    else:
        return "Low"
    
def calculate_priority(category):
    critical_categories = ["fire", "water", "electricity"]
    high_categories = ["road", "traffic"]

    if category in critical_categories:
        return "critical"
    elif category in high_categories:
        return "high"
    elif category in ["pollution", "garbage"]:
        return "medium"
    else:
        return "low"


# ==================================================
# BASIC ROUTES
# ==================================================
@app.route("/")
def index():

    total = Complaint.query.count()
    resolved = Complaint.query.filter_by(status="Resolved").count()

    critical = Complaint.query.filter(
        Complaint.category.in_(["fire", "water", "electricity"])
    ).count()

    rate = 0
    if total > 0:
        rate = round((resolved / total) * 100)

    # 🔥 LIVE PRIORITY ISSUES (TOP 3 UNRESOLVED)
    live_issues = Complaint.query.filter(
        Complaint.status != "Resolved"
    ).order_by(Complaint.created_at.desc()).limit(3).all()

    return render_template(
        "index.html",
        total=total,
        resolved=resolved,
        critical=critical,
        rate=rate,
        live_issues=live_issues,
        get_priority=get_priority
    )

from flask import session

from flask import session, flash

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        role = request.form.get("role")
        email = request.form.get("email")
        password = request.form.get("password")

        print(role, email, password)   # 👈 DEBUG (watch terminal)

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("❌ User not registered. Please signup first")
            return redirect("/login")

        if user.password != password:
            flash("❌ Incorrect password")
            return redirect("/login")

        if user.role != role:
            flash("❌ Incorrect role selected")
            return redirect("/login")

        session["user"] = user.name
        session["role"] = user.role

        flash("✅ Login Successful!")

        if role == "Admin":
            return redirect("/admin")
        elif role == "Officer":
            return redirect("/officer-dashboard")  # you can create this page later
        else:
            return redirect("/")

    return render_template("login.html")




@app.route("/signup", methods=["GET","POST"])
def signup():

    if request.method == "POST":

        username = request.form.get("username")
        mobile = request.form.get("mobile")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("❌ Account already registered. Please login.")
            return redirect("/signup")

        new_user = User(
            name=username,
            mobile=mobile,
            email=email,
            password=password,
            role="Citizen"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("✅ Account Created Successfully! Please Login.")
        return redirect("/login")

    return render_template("signup.html")


@app.route("/departments")
def departments():

    # ✅ Only citizens can access
    if session.get("role") != "Citizen":
        return redirect("/login")

    # you can keep static OR dynamic
    departments = Department.query.all()

    return render_template(
        "departments.html",
        departments=departments
    )


@app.route("/officer-dashboard")
def officer_dashboard():

    # 🔒 Only Officer or Admin allowed
    if session.get("role") not in ["Officer", "Admin"]:
        return redirect("/login")

    # 🔥 Show complaints assigned to departments
    complaints = Complaint.query.filter(
        Complaint.assigned_department != None
    ).order_by(Complaint.created_at.desc()).all()

    total = len(complaints)
    resolved = Complaint.query.filter_by(status="Resolved").count()
    in_progress = Complaint.query.filter_by(status="In Progress").count()

    return render_template(
        "officer-dashboard.html",
        complaints=complaints,
        total=total,
        resolved=resolved,
        in_progress=in_progress
    )


@app.route("/admin")
def admin():
    if session.get("role") != "Admin":
        return redirect("/login")
    
    complaints = Complaint.query.all()

    # -------- PRIORITY COUNTS --------
    critical_count = Complaint.query.filter(
        Complaint.category.in_(["fire", "water", "electricity"])
    ).count()

    high_count = Complaint.query.filter(
        Complaint.category.in_(["road", "traffic"])
    ).count()

    medium_count = Complaint.query.filter(
        Complaint.category.in_(["pollution", "garbage"])
    ).count()

    low_count = Complaint.query.filter(
        Complaint.category.in_(["parking", "animal", "grievance"])
    ).count()

    # -------- DEPARTMENT WORKLOAD (THIS WAS MISSING) --------
    dept_workload = {
        "Public Works Department": Complaint.query.filter_by(category="road").count(),
        "Water Supply Department": Complaint.query.filter_by(category="water").count(),
        "Municipal Sanitation": Complaint.query.filter_by(category="garbage").count(),
        "Electricity Department": Complaint.query.filter_by(category="electricity").count(),
        "Fire & Emergency": Complaint.query.filter_by(category="fire").count()
    }

    return render_template(
        "admin.html",
        data=complaints,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        dept_workload=dept_workload   # ✅ THIS FIXES THE ERROR
    )

@app.route("/assign", methods=["GET", "POST"])
def assign():
    if request.method == "POST":
        cid = request.form.get("complaint_id")
        department = request.form.get("department")

        complaint = Complaint.query.filter_by(complaint_id=cid).first()
        if complaint:
            complaint.assigned_department = department
            complaint.status = "In Progress"   # auto update
            db.session.commit()

        return redirect(url_for("assign"))

    # show only unassigned / registered complaints
    complaints = Complaint.query.filter_by(status="Registered").all()
    return render_template(
        "assign.html",
        complaints=complaints,
        get_priority=get_priority
    )



@app.route("/notices")
def notices():
    return render_template("notices.html")

# ==================================================
# DEPARTMENT PAGES
# ==================================================
@app.route("/public-works")
def public_works():
    return render_template("public-works.html")

@app.route("/water-supply")
def water_supply():
    return render_template("water-supply.html")

@app.route("/electricity")
def electricity():
    return render_template("electricity.html")

@app.route("/sanitation")
def sanitation():
    return render_template("sanitation.html")

@app.route("/traffic")
def traffic():
    return render_template("traffic.html")

@app.route("/fire-emergency")
def fire_emergency():
    return render_template("fire-emergency.html")

@app.route("/animal-control")
def animal_control():
    return render_template("animal-control.html")

@app.route("/pollution-control")
def pollution_control():
    return render_template("pollution-control.html")

@app.route("/public-grievance")
def public_grievance():
    return render_template("public-grievance.html")

@app.route("/manage-departments", methods=["GET", "POST"])
def manage_departments():

    if session.get("role") != "Admin":
        return redirect("/login")

    # 🔥 ADD NEW DEPARTMENT
    if request.method == "POST":

        name = request.form.get("name")
        officer = request.form.get("officer")
        email = request.form.get("email")
        status = request.form.get("status")

        exists = Department.query.filter_by(name=name).first()

        if not exists:
            new_dept = Department(
                name=name,
                head_officer=officer,
                email=email,
                status=status
            )
            db.session.add(new_dept)
            db.session.commit()

    departments = Department.query.all()

    # 🔥 AUTO COUNT ACTIVE COMPLAINTS
    dept_data = []

    for d in departments:
        active = Complaint.query.filter_by(
            assigned_department=d.name
        ).count()

        dept_data.append({
            "name": d.name,
            "officer": d.head_officer,
            "email": d.email,
            "status": d.status,
            "active": active
        })

    return render_template(
        "manage-departments.html",
        departments=dept_data
    )



# ==================================================
# REGISTER COMPLAINT
# ==================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("role") != "Citizen":
        return redirect(url_for("login"))

    if request.method == "POST":
        print(request.form)
        complaint_id = "UFX" + str(random.randint(100000, 999999))

        complaint = Complaint(
            complaint_id=complaint_id,
            name=request.form.get("name"),
            mobile=request.form.get("mobile"),
            category=request.form.get("category"),
            description=request.form.get("description"),
            area=request.form.get("area"),
            complaint_type="complaint",
            priority=calculate_priority(request.form.get("category")),
            status="Registered"
        )

        db.session.add(complaint)
        db.session.commit()
        

        return redirect(url_for("success", complaint_id=complaint_id))

    return render_template("register.html")

# ==================================================
# REGISTER PUBLIC GRIEVANCE
# ==================================================
@app.route("/public-grievance-register", methods=["GET", "POST"])
def public_grievance_register():
    if request.method == "POST":
        grievance_id = "GRV" + str(random.randint(100000, 999999))

        grievance = Complaint(
            complaint_id=grievance_id,
            name=request.form.get("name"),
            mobile=request.form.get("mobile"),
            category="Public Grievance",
            description=request.form.get("description"),
            complaint_type="grievance"
        )

        db.session.add(grievance)
        db.session.commit()

        return redirect(url_for("generate_pdf", cid=grievance_id))

    return render_template("public-grievance-register.html")

# ==================================================
# TRACK COMPLAINT
# ==================================================
@app.route("/track", methods=["GET", "POST"])
def track():
    complaint = None
    if request.method == "POST":
        cid = request.form.get("complaint_id")
        complaint = Complaint.query.filter_by(complaint_id=cid).first()

    return render_template("track.html", data=complaint)


# ==================================================
# PDF ACKNOWLEDGMENT
# ==================================================
@app.route("/pdf/<cid>")
def generate_pdf(cid):
    os.makedirs("uploads", exist_ok=True)
    pdf_path = os.path.join("uploads", f"{cid}.pdf")

    complaint = Complaint.query.filter_by(complaint_id=cid).first()

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    # ================= WATERMARK =================
    c.saveState()
    c.setFont("Helvetica-Bold", 50)
    c.setFillColorRGB(0.85, 0.85, 0.85)  # light grey
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, "DIGITAL OFFICIAL COPY")
    c.restoreState()

    # ================= HEADER =================
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "GOVERNMENT OF INDIA")

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 75, "UrbanFix Portal")

    c.setFont("Helvetica", 11)
    c.drawCentredString(
        width / 2,
        height - 95,
        "Smart City Civic Complaint System"
    )

    c.line(40, height - 115, width - 40, height - 115)

    # ================= TITLE =================
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 155, "ACKNOWLEDGMENT RECEIPT")

    # ================= DETAILS =================
    c.setFont("Helvetica", 11)
    y = height - 200
    gap = 22

    def row(label, value):
        nonlocal y
        c.drawString(60, y, label)
        c.drawString(260, y, f": {value}")
        y -= gap

    row("Complaint Reference ID", complaint.complaint_id)
    row("Citizen Name", complaint.name)
    row("Mobile Number", complaint.mobile)
    row("Complaint Type", complaint.complaint_type.capitalize())
    row("Category", complaint.category)
    row("Status", complaint.status)
    row("Date & Time", complaint.created_at.strftime("%d-%m-%Y %H:%M"))

    # ================= QR CODE =================
    qr_data = f"UrbanFix Complaint ID: {complaint.complaint_id}"
    qr_code = qr.QrCodeWidget(qr_data)
    bounds = qr_code.getBounds()
    size = 90

    width_qr = bounds[2] - bounds[0]
    height_qr = bounds[3] - bounds[1]
    transform = [
        size / width_qr, 0, 0,
        size / height_qr, 0, 0
    ]

    drawing = Drawing(size, size, transform=transform)
    drawing.add(qr_code)
    renderPDF.draw(drawing, c, width - 140, height - 300)

    c.setFont("Helvetica", 9)
    c.drawCentredString(width - 95, height - 310, "Scan to Verify")

    # ================= BARCODE =================
    base_y = 170  # common baseline for alignment

    # BARCODE (LEFT)
    barcode = code128.Code128(
        complaint.complaint_id,
        barHeight=40,
        barWidth=1.2
    )
    barcode.drawOn(c, 60, base_y)

    c.setFont("Helvetica", 9)
    c.drawString(100, 145, "Complaint ID Barcode")

    # DIGITAL SIGNATURE (RIGHT)
    sig_x = width - 160

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(sig_x, base_y + 25, "Digitally signed by")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(sig_x, base_y + 10, "Rajat Kumar")
    c.setFont("Helvetica", 9)
    c.drawString(sig_x, base_y - 5, "UrbanFix Portal")

    c.drawString(
        sig_x,
        base_y - 20,
        "Date: " + datetime.now().strftime("%d-%m-%Y")
    )

    # ================= FOOTER =================
    c.line(40, 120, width - 40, 120)
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(
        width / 2, 100,
        "This is a system-generated acknowledgment. No physical signature is required."
    )
    c.drawCentredString(
        width / 2, 85,
        "© 2026 UrbanFix Portal | Government of India"
    )

    c.save()
    return send_file(pdf_path, as_attachment=True)




@app.route("/success/<complaint_id>")
def success(complaint_id):
    return render_template("success.html", complaint_id=complaint_id)

@app.route("/update-status", methods=["GET", "POST"])
def update_status():
    if request.method == "POST":
        cid = request.form.get("complaint_id")
        new_status = request.form.get("status")
        remarks = request.form.get("remarks")

        complaint = Complaint.query.filter_by(complaint_id=cid).first()

        if complaint:
            complaint.status = new_status
            complaint.remarks = remarks

            # 🔥 AUTO TIMELINE UPDATE
            if new_status == "Assigned" and not complaint.assigned_at:
                complaint.assigned_at = datetime.now()

            elif new_status == "In Progress" and not complaint.in_progress_at:
                complaint.in_progress_at = datetime.now()

            elif new_status == "Resolved" and not complaint.resolved_at:
                complaint.resolved_at = datetime.now()

            db.session.commit()

        return redirect("/update-status")

    # 🔹 FETCH ALL COMPLAINTS FROM DATABASE
    complaints = Complaint.query.all()
    return render_template("update-status.html", complaints=complaints)

    #return redirect(url_for("admin"))

@app.route("/officer-update-status", methods=["GET", "POST"])
def officer_update_status():

    # 🔒 Only Officer allowed
    if session.get("role") != "Officer":
        return redirect("/login")

    if request.method == "POST":

        cid = request.form.get("complaint_id")
        new_status = request.form.get("status")
        remarks = request.form.get("remarks")

        complaint = Complaint.query.filter_by(complaint_id=cid).first()

        if complaint:
            complaint.status = new_status

            if new_status == "In Progress" and not complaint.in_progress_at:
                complaint.in_progress_at = datetime.now()

            elif new_status == "Resolved" and not complaint.resolved_at:
                complaint.resolved_at = datetime.now()

            db.session.commit()

        return redirect("/officer-update-status")

    # 🔥 THIS WAS MISSING → RETURN TEMPLATE
    complaints = Complaint.query.filter(
        Complaint.assigned_department.isnot(None)
    ).all()

    return render_template(
        "officer-update-status.html",
        complaints=complaints
    )

@app.route("/reports")
def reports():
    complaints = Complaint.query.all()

    total = Complaint.query.count()
    resolved = Complaint.query.filter_by(status="Resolved").count()
    in_progress = Complaint.query.filter_by(status="In Progress").count()
    critical_pending = Complaint.query.filter_by(priority="Critical", status="Registered").count()

    departments = [
        "Public Works Department",
        "Water Supply Department",
        "Municipal Sanitation",
        "Electricity Department",
        "Traffic Police"
    ]

    dept_stats = []

    for dept in departments:
        total_d = Complaint.query.filter_by(assigned_department=dept).count()
        resolved_d = Complaint.query.filter_by(assigned_department=dept, status="Resolved").count()
        in_progress_d = Complaint.query.filter_by(assigned_department=dept, status="In Progress").count()
        pending_d = Complaint.query.filter_by(assigned_department=dept, status="Registered").count()

        dept_stats.append({
            "name": dept,
            "total": total_d,
            "resolved": resolved_d,
            "in_progress": in_progress_d,
            "pending": pending_d,
            "avg_time": "—"
        })

    return render_template(
        "reports.html",
        complaints=complaints,
        total=total,
        resolved=resolved,
        in_progress=in_progress,
        critical_pending=critical_pending,
        dept_stats=dept_stats
    )

@app.route("/export-pdf")
def export_pdf():

    os.makedirs("exports", exist_ok=True)

    file_path = "exports/reports.pdf"

    complaints = Complaint.query.all()

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "UrbanFix Complaint Report")
    y -= 40

    c.setFont("Helvetica", 10)

    for comp in complaints:

        text = f"{comp.complaint_id} | {comp.category} | {comp.status} | {comp.assigned_department or 'Not Assigned'}"

        c.drawString(40, y, text)

        y -= 20

        if y < 50:
            c.showPage()
            y = height - 40

    c.save()

    return send_file(file_path, as_attachment=True)

@app.route("/export-excel")
def export_excel():

    os.makedirs("exports", exist_ok=True)

    file_path = "exports/reports.xlsx"

    wb = Workbook()
    ws = wb.active

    ws.append([
        "Complaint ID",
        "Category",
        "Priority",
        "Status",
        "Department",
        "Date"
    ])

    complaints = Complaint.query.all()

    for c in complaints:
        ws.append([
            c.complaint_id,
            c.category,
            c.priority,
            c.status,
            c.assigned_department,
            c.created_at.strftime("%d-%m-%Y")
        ])

    wb.save(file_path)

    return send_file(file_path, as_attachment=True)


@app.route("/logout")
def logout():
    session.clear()     # remove login session
    return redirect("/")   # go back to home




# ==================================================
# START APPLICATION
# ==================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email="admin@urbanfix.gov.in").first()
        if not admin:
            admin = User(
                name="Admin",
                email="admin@urbanfix.gov.in",
                password="admin123",
                role="Admin"
            )
            db.session.add(admin)

        officer = User.query.filter_by(email="officer@urbanfix.gov.in").first()
        if not officer:
            officer = User(
                name="Officer",
                email="officer@urbanfix.gov.in",
                password="officer123",
                role="Officer"
            )
            db.session.add(officer)

        db.session.commit()
    app.run(debug=True)
