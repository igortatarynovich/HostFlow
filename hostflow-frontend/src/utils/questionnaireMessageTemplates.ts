export type QuestionnaireSendChannel = 'email' | 'whatsapp' | 'link'

export type TemplateLocale = 'ru' | 'pl' | 'en'

export type QuestionnaireMessageContext = {
  applyUrl: string
  contactName?: string
  managerName?: string
  companyName?: string
}

export type QuestionnaireInvitationTemplates = {
  emailSubject: string
  emailBody: string
  whatsAppMessage: string
}

function pickLocale(locale: string | undefined): TemplateLocale {
  const code = String(locale || 'ru').trim().toLowerCase()
  if (code.startsWith('pl')) return 'pl'
  if (code.startsWith('en')) return 'en'
  return 'ru'
}

function greetingName(ctx: QuestionnaireMessageContext, locale: TemplateLocale): string {
  const name = ctx.contactName?.trim()
  if (!name) {
    if (locale === 'pl') return 'Dzień dobry,'
    if (locale === 'en') return 'Hello,'
    return 'Здравствуйте!'
  }
  if (locale === 'pl') return `Dzień dobry ${name},`
  if (locale === 'en') return `Hello ${name},`
  return `Здравствуйте, ${name}!`
}

function managerLine(ctx: QuestionnaireMessageContext, locale: TemplateLocale): string {
  const manager = ctx.managerName?.trim() || (locale === 'pl' ? '[Imię menedżera]' : locale === 'en' ? '[Manager name]' : '[Имя менеджера]')
  const company = ctx.companyName?.trim()
  if (locale === 'pl') return company ? `${manager}\n${company}` : manager
  if (locale === 'en') return company ? `${manager}\n${company}` : manager
  return company ? `${manager}\n${company}` : manager
}

export function questionnaireInvitationTemplates(
  ctx: QuestionnaireMessageContext,
  localeInput?: string,
): QuestionnaireInvitationTemplates {
  const locale = pickLocale(localeInput)

  if (locale === 'pl') {
    const greeting = greetingName(ctx, locale)
    return {
      emailSubject: 'Dziękujemy za kontakt — kilka dodatkowych pytań',
      emailBody: [
        greeting,
        '',
        'Dziękujemy za zainteresowanie naszymi usługami.',
        '',
        'Aby przygotować odpowiednią propozycję, potrzebujemy kilku dodatkowych informacji.',
        'Prosimy o wypełnienie krótkiego formularza pod poniższym linkiem.',
        '',
        ctx.applyUrl,
        '',
        'Po otrzymaniu odpowiedzi przeanalizujemy informacje i skontaktujemy się z Państwem.',
        '',
        'Pozdrawiam,',
        managerLine(ctx, locale),
      ].join('\n'),
      whatsAppMessage: [
        greeting.replace(/,$/, '!'),
        '',
        'Dziękujemy za kontakt.',
        '',
        'Aby przygotować dla Państwa propozycję i ocenić, jak najlepiej pomóc, prosimy o wypełnienie krótkiego formularza.',
        'Zajmie to około 2–3 minut.',
        '',
        ctx.applyUrl,
        '',
        'Po otrzymaniu odpowiedzi skontaktujemy się w sprawie dalszych kroków.',
      ].join('\n'),
    }
  }

  if (locale === 'en') {
    const greeting = greetingName(ctx, locale)
    return {
      emailSubject: 'Thank you for reaching out — a few quick questions',
      emailBody: [
        greeting,
        '',
        'Thank you for your interest in our services.',
        '',
        'To prepare a suitable proposal, we need a few additional details.',
        'Please complete the short form at the link below.',
        '',
        ctx.applyUrl,
        '',
        'Once we receive your answers, we will review them and get back to you.',
        '',
        'Best regards,',
        managerLine(ctx, locale),
      ].join('\n'),
      whatsAppMessage: [
        greeting.replace(/,$/, '!'),
        '',
        'Thank you for reaching out.',
        '',
        'To prepare a proposal and understand how we can help, please complete a short form.',
        'It takes about 2–3 minutes.',
        '',
        ctx.applyUrl,
        '',
        'We will contact you after we receive your answers.',
      ].join('\n'),
    }
  }

  const greeting = greetingName(ctx, locale)
  return {
    emailSubject: 'Спасибо за обращение — несколько уточняющих вопросов',
    emailBody: [
      greeting.endsWith('!') ? greeting.replace('!', ',') : greeting,
      '',
      'Спасибо за ваш интерес к нашим услугам.',
      '',
      'Чтобы подготовить подходящее предложение, нам понадобится несколько дополнительных сведений.',
      'Пожалуйста, заполните короткую форму по ссылке ниже.',
      '',
      ctx.applyUrl,
      '',
      'После получения ответов мы изучим информацию и свяжемся с вами.',
      '',
      'С уважением,',
      managerLine(ctx, locale),
    ].join('\n'),
    whatsAppMessage: [
      greeting,
      '',
      'Спасибо за обращение.',
      '',
      'Чтобы мы могли подготовить для вас предложение и оценить, как лучше помочь, пожалуйста, заполните короткую форму.',
      'Это займёт около 2–3 минут.',
      '',
      ctx.applyUrl,
      '',
      'После получения ответов мы свяжемся с вами и обсудим дальнейшие шаги.',
    ].join('\n'),
  }
}

/** @deprecated use questionnaireInvitationTemplates */
export function defaultQuestionnaireEmailSubject(): string {
  return questionnaireInvitationTemplates({ applyUrl: '' }, 'pl').emailSubject
}

/** @deprecated use questionnaireInvitationTemplates */
export function defaultQuestionnaireEmailBody(ctx: QuestionnaireMessageContext): string {
  return questionnaireInvitationTemplates(ctx, 'pl').emailBody
}

/** @deprecated use questionnaireInvitationTemplates */
export function defaultQuestionnaireWhatsAppMessage(ctx: QuestionnaireMessageContext): string {
  return questionnaireInvitationTemplates(ctx, 'pl').whatsAppMessage
}

export function buildQuestionnaireMailtoUrl(email: string, subject: string, body: string): string {
  const params = new URLSearchParams()
  if (subject.trim()) params.set('subject', subject)
  if (body.trim()) params.set('body', body)
  const query = params.toString()
  return `mailto:${email.trim()}${query ? `?${query}` : ''}`
}
