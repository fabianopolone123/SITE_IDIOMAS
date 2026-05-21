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
        title='Autorizacao para viagem de menor de idade',
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

    data = [
        [Paragraph('Responsavel legal', label), Paragraph(registration.responsible_name, body)],
        [Paragraph('RG do responsavel', label), Paragraph(registration.responsible_rg, body)],
        [Paragraph('CPF do responsavel', label), Paragraph(registration.responsible_cpf, body)],
        [Paragraph('Nome do(a) menor', label), Paragraph(registration.minor_name, body)],
        [Paragraph('Nascimento do(a) menor', label), Paragraph(registration.minor_birth_date.strftime('%d/%m/%Y'), body)],
        [Paragraph('RG/CPF do(a) menor', label), Paragraph(registration.minor_document or 'Nao informado', body)],
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
        Paragraph('AUTORIZACAO PARA VIAGEM DE MENOR DE IDADE', title),
        Paragraph(
            'Projeto "Passaporte: Sua Identidade em Alta Definicao" - CATRE de Analandia/SP',
            small,
        ),
        Spacer(1, 0.25 * cm),
        table,
        Spacer(1, 0.35 * cm),
        Paragraph(
            f'Eu, <b>{registration.responsible_name}</b>, portador(a) do RG no '
            f'<b>{registration.responsible_rg}</b> e CPF no <b>{registration.responsible_cpf}</b>, '
            'na qualidade de pai/mae ou responsavel legal pelo(a) adolescente indicado(a) acima, '
            'autorizo sua participacao no projeto "Passaporte: Sua Identidade em Alta Definicao", '
            'que sera realizado no CATRE de Analandia/SP.',
            body,
        ),
        Paragraph(
            'Declaro estar ciente de que os adolescentes sairao da IASD Central de Sao Carlos '
            'as 7h da manha, com destino ao CATRE de Analandia, em transporte realizado por '
            f'<b>{registration.transport_by}</b>.',
            body,
        ),
        Paragraph(
            'Tambem declaro estar ciente de que o retorno sera realizado igualmente de van, '
            'do CATRE de Analandia para a IASD Central de Sao Carlos, apos o encerramento das '
            'atividades programadas.',
            body,
        ),
        Spacer(1, 1.1 * cm),
        Paragraph('Sao Carlos/SP, ____ de ____________________ de 2026.', body),
        Spacer(1, 1.4 * cm),
        Paragraph('_______________________________________________', body),
        Paragraph('Assinatura do pai/mae ou responsavel legal', small),
        Spacer(1, 0.45 * cm),
        Paragraph(
            'Orientacao: assine digitalmente pelo portal oficial gov.br/assinatura ou pelo '
            'portal assinador.iti.br, baixe o PDF assinado e envie novamente no sistema.',
            small,
        ),
    ]

    doc.build(story)
    buffer.seek(0)
    return buffer
