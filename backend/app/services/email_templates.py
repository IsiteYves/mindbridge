import html

FONT_STACK = "Geist, Arial, Helvetica, sans-serif"
MONO_STACK = "'Geist Mono', Menlo, Consolas, monospace"
CODE_TTL_MINUTES = 10

CODE_COPY = {
    "signup": (
        "Verify your MindBridge email",
        "Verify your email",
        "Enter this code to confirm your email address and finish creating your account.",
    ),
    "email_change": (
        "Confirm your new MindBridge email",
        "Confirm your new email",
        "Enter this code to confirm the new email address on your account.",
    ),
    "reset": (
        "Reset your MindBridge password",
        "Reset your password",
        "Enter this code to choose a new password for your account.",
    ),
}


def _esc(value):
    return html.escape(str(value), quote=True)


def _paragraph(text, muted=False):
    color = "#5a6e72" if muted else "#12262c"
    size = "13px" if muted else "15px"
    return f'<p style="margin:0 0 14px;font-size:{size};line-height:1.6;color:{color};">{_esc(text)}</p>'


def _layout(heading, inner, preheader):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(heading)}</title>
</head>
<body style="margin:0;padding:0;background:#eef5f4;font-family:{FONT_STACK};color:#12262c;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{_esc(preheader)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef5f4;">
<tr>
<td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;">
<tr>
<td style="padding:0 0 16px;">
<span style="display:inline-block;width:30px;height:30px;line-height:30px;border-radius:9px;background:#0f766e;color:#ffffff;text-align:center;font-weight:800;font-size:15px;vertical-align:middle;">M</span>
<span style="display:inline-block;margin-left:8px;font-weight:800;font-size:17px;color:#10242b;vertical-align:middle;">MindBridge</span>
</td>
</tr>
<tr>
<td style="background:#ffffff;border:1px solid rgba(18,38,44,0.09);border-radius:16px;padding:30px 32px;">
<h1 style="margin:0 0 14px;font-size:22px;line-height:1.3;font-weight:800;color:#10242b;">{_esc(heading)}</h1>
{inner}
</td>
</tr>
<tr>
<td style="padding:18px 8px 0;font-size:12px;line-height:1.6;color:#5a6e72;text-align:center;">
MindBridge does not diagnose or treat mental health.<br>
You are receiving this because of activity on your MindBridge account.
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""


def code_email(purpose, code):
    subject, heading, intro = CODE_COPY[purpose]
    text = (
        f"{intro}\n\nYour code: {code}\n\n"
        f"It expires in {CODE_TTL_MINUTES} minutes. If you did not ask for this, you can ignore this email."
    )
    box = (
        '<div style="margin:6px 0 22px;padding:20px 12px;border:1px solid rgba(18,38,44,0.17);border-radius:12px;'
        'background:#eef5f4;text-align:center;">'
        f'<span style="font-family:{MONO_STACK};font-size:32px;font-weight:700;letter-spacing:10px;color:#0f766e;">'
        f"{_esc(code)}</span></div>"
    )
    inner = (
        _paragraph(intro)
        + box
        + _paragraph(f"It expires in {CODE_TTL_MINUTES} minutes.", muted=True)
        + _paragraph("If you did not ask for this, you can ignore this email.", muted=True)
    )
    return subject, text, _layout(heading, inner, preheader=f"Your MindBridge code is {code}")


def message_email(subject, body):
    paragraphs = [chunk.strip() for chunk in body.split("\n\n") if chunk.strip()]
    inner = "".join(_paragraph(chunk) for chunk in paragraphs)
    return body, _layout(subject, inner, preheader=paragraphs[0] if paragraphs else subject)
