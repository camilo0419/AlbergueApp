# ui/pdf_utils.py
from tkinter import messagebox

def render_pdf_from_html(html: str, out_path: str) -> bool:
    """Genera un PDF a partir de un string HTML. Usa WeasyPrint si está disponible,
    de lo contrario intenta con xhtml2pdf."""
    try:
        from weasyprint import HTML  # type: ignore[import-not-found]
        HTML(string=html).write_pdf(out_path)
        return True
    except Exception:
        try:
            from xhtml2pdf import pisa
            with open(out_path, "wb") as f:
                pisa.CreatePDF(html, dest=f)
            return True
        except Exception as e:
            messagebox.showerror("PDF", f"No se pudo generar PDF: {e}")
            return False
