from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_authorization_pdf(registration):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title='Autorização para uso de imagem e atendimento emergencial',
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        'VanTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#111827'),
        spaceAfter=10,
    )
    body = ParagraphStyle(
        'VanBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#111827'),
        spaceAfter=8,
    )
    label = ParagraphStyle(
        'VanLabel',
        parent=body,
        fontName='Helvetica-Bold',
        spaceAfter=0,
    )
    small = ParagraphStyle(
        'VanSmall',
        parent=body,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#4b5563'),
    )

    def format_date(value):
        return value.strftime('%d/%m/%Y') if value else '____/____/________'

    event_date = format_date(registration.event_start_date)
    signature_date = format_date(registration.signature_date)
    phone_alt = registration.responsible_phone_alt_formatted or 'Não informado'
    health_info = registration.health_info or 'Nenhuma informação adicional registrada.'

    data = [
        [Paragraph('Responsável legal', label), Paragraph(registration.responsible_name, body)],
        [Paragraph('CPF do responsável', label), Paragraph(registration.responsible_cpf_formatted, body)],
        [Paragraph('Adolescente', label), Paragraph(registration.minor_name, body)],
        [Paragraph('CPF do adolescente', label), Paragraph(registration.minor_cpf_formatted or 'Não informado', body)],
        [Paragraph('Evento', label), Paragraph(registration.event_name, body)],
        [Paragraph('Data do evento', label), Paragraph(event_date, body)],
    ]
    table = Table(data, colWidths=[5.1 * cm, 10.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#d1d5db')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )

    story = [
        Paragraph('AUTORIZAÇÃO PARA USO DE IMAGEM E ATENDIMENTO EMERGENCIAL', title),
        Paragraph(
            registration.event_name,
            small,
        ),
        Spacer(1, 0.25 * cm),
        table,
        Spacer(1, 0.35 * cm),
        Paragraph(
            f'Eu, <b>{registration.responsible_name}</b>, portador(a) do CPF nº '
            f'<b>{registration.responsible_cpf_formatted}</b>, responsável legal por '
            f'<b>{registration.minor_name}</b>, autorizo sua participação no evento '
            f'<b>{registration.event_name}</b>, realizado no dia <b>{event_date}</b>.',
            body,
        ),
        Paragraph('<b>Autorizo, também:</b>', body),
        Paragraph(
            '<b>1. Uso de imagem e voz</b><br/>'
            'O uso gratuito de fotos, vídeos e gravações de voz realizados durante o evento, '
            'para fins de divulgação em redes sociais, materiais institucionais, apresentações '
            'e demais meios relacionados às atividades do evento, sem finalidade comercial.',
            body,
        ),
        Paragraph(
            '<b>2. Atendimento em situação de emergência</b><br/>'
            'Em caso de emergência médica, autorizo os responsáveis pelo evento a providenciarem '
            'atendimento médico, hospitalar ou remoção para unidade de saúde, caso não seja possível '
            'contato imediato com os responsáveis legais.',
            body,
        ),
        Spacer(1, 0.2 * cm),
        Paragraph('<b>Informações importantes de saúde:</b>', label),
        Paragraph(health_info.replace('\n', '<br/>'), body),
        Spacer(1, 0.15 * cm),
        Paragraph('<b>Telefone dos responsáveis:</b>', label),
        Paragraph(f'{registration.responsible_phone_formatted}<br/>{phone_alt}', body),
        Spacer(1, 0.25 * cm),
        Paragraph(f'Cidade: <b>{registration.city or "________________"}</b>', body),
        Paragraph(f'Data: <b>{signature_date}</b>', body),
        Spacer(1, 0.95 * cm),
        Paragraph('_______________________________________________', body),
        Paragraph('Assinatura do responsável legal', small),
        Spacer(1, 0.55 * cm),
        Paragraph('_______________________________________________', body),
        Paragraph('Nome completo do responsável legal', small),
        Spacer(1, 0.45 * cm),
        Paragraph(
            'Orientação: assine digitalmente pelo portal oficial gov.br/assinatura ou pelo '
            'portal assinador.iti.br, baixe o PDF assinado e envie novamente no sistema.',
            small,
        ),
    ]

    doc.build(story)
    buffer.seek(0)
    return buffer
