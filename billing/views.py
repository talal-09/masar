from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from customers.access import customer_required, get_owned_or_403

from .models import Invoice


def rtl(text):
    return get_display(arabic_reshaper.reshape(str(text)))


@customer_required
def invoice_list(request):
    invoices = (
        Invoice.objects.filter(work_order__customer=request.customer)
        .select_related("work_order", "work_order__vehicle")
        .order_by("-created_at")
    )
    query = request.GET.get("q", "").strip()[:100]
    status = request.GET.get("status", "").strip()
    if query:
        invoices = invoices.filter(
            Q(work_order__vehicle__brand__icontains=query)
            | Q(work_order__vehicle__model__icontains=query)
            | Q(work_order__vehicle__plate_number__icontains=query)
        )
    valid_statuses = {value for value, _ in Invoice.STATUS}
    if status in valid_statuses:
        invoices = invoices.filter(status=status)
    page = Paginator(invoices, 10).get_page(request.GET.get("page"))
    return render(request, "billing/invoice_list.html", {
        "invoices": page,
        "page_obj": page,
        "query": query,
        "selected_status": status,
        "status_choices": Invoice.STATUS,
        "results_count": page.paginator.count,
    })


@customer_required
def invoice_detail(request, pk):
    invoice = get_owned_or_403(Invoice, request.customer, pk=pk)
    invoice = (
        Invoice.objects.select_related("work_order", "work_order__vehicle")
        .prefetch_related("items", "payments")
        .get(pk=invoice.pk)
    )
    return render(request, "billing/invoice_detail.html", {"invoice": invoice})


@customer_required
def invoice_pdf(request, pk):
    invoice = get_owned_or_403(Invoice, request.customer, pk=pk)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_candidates = [
        (
            Path("C:/Windows/Fonts/tahoma.ttf"),
            Path("C:/Windows/Fonts/tahomabd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    regular_font, bold_font = next(
        (
            (regular, bold)
            for regular, bold in font_candidates
            if regular.exists() and bold.exists()
        ),
        (None, None),
    )
    if regular_font is None:
        raise RuntimeError("Arabic TTF font is required to generate invoices.")
    pdfmetrics.registerFont(TTFont("Arabic", str(regular_font)))
    pdfmetrics.registerFont(TTFont("ArabicBold", str(bold_font)))

    pdf.setFillColor(colors.HexColor("#0f766e"))
    pdf.roundRect(36, height - 130, width - 72, 90, 18, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("ArabicBold", 24)
    pdf.drawRightString(width - 58, height - 78, rtl("مَسَار"))
    pdf.setFont("Arabic", 11)
    pdf.drawRightString(width - 58, height - 102, rtl("فاتورة صيانة"))
    pdf.drawString(58, height - 86, f"INV-{invoice.pk}")

    y = height - 175
    details = [
        ("العميل", invoice.work_order.customer.full_name),
        ("المركبة", str(invoice.work_order.vehicle)),
        ("أمر الصيانة", f"WO-{invoice.work_order_id}"),
        ("تاريخ الفاتورة", invoice.created_at.strftime("%Y/%m/%d")),
        ("حالة السداد", invoice.get_status_display()),
    ]
    pdf.setFillColor(colors.HexColor("#0f172a"))
    for label, value in details:
        pdf.setFont("ArabicBold", 11)
        pdf.drawRightString(width - 58, y, rtl(label))
        pdf.setFont("Arabic", 11)
        pdf.drawRightString(width - 190, y, rtl(value))
        pdf.setStrokeColor(colors.HexColor("#e2e8f0"))
        pdf.line(58, y - 12, width - 58, y - 12)
        y -= 38

    y -= 15
    amounts = [
        ("المجموع الفرعي", invoice.subtotal),
        ("الضريبة", invoice.tax),
        ("الإجمالي", invoice.total),
    ]
    for label, amount in amounts:
        if label == "الإجمالي":
            pdf.setFillColor(colors.HexColor("#ecfdf5"))
            pdf.roundRect(58, y - 15, width - 116, 38, 10, fill=1, stroke=0)
            pdf.setFillColor(colors.HexColor("#0f766e"))
            pdf.setFont("ArabicBold", 13)
        else:
            pdf.setFillColor(colors.HexColor("#334155"))
            pdf.setFont("Arabic", 11)
        pdf.drawRightString(width - 75, y, rtl(label))
        pdf.drawString(75, y, f"{amount:,.2f} SAR")
        y -= 44

    pdf.setFillColor(colors.HexColor("#64748b"))
    pdf.setFont("Arabic", 9)
    pdf.drawCentredString(width / 2, 45, rtl("شكرًا لاختياركم مَسَار"))
    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="invoice-{invoice.pk}.pdf"'
    )
    return response
