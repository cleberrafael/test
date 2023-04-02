import logging
import os
from datetime import datetime

import openai
import stripe
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

# Configurar as chaves de API
OPENAI_API_KEY = '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'
STRIPE_API_KEY = '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'
TELEGRAM_BOT_TOKEN = '5990910419:AAFoG6PQjCQ26Nf3jMPec12MRlAvG4aFS78'

# Configurar planos de assinatura
PLAN_ID = 'price_1Ms9FxJgKx6RCg9NuHQ9SOUs'

# Definir limite de mensagens para usuários não assinantes
MESSAGE_LIMIT = 5

# Configurar log
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurar OpenAI
openai.api_key = OPENAI_API_KEY

# Configurar Stripe
stripe.api_key = STRIPE_API_KEY

# Definir data atual
today = datetime.today().strftime('%Y-%m-%d')

# Definir dicionário de usuários
users = {}

# Função para tratar comando /start
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    
    # Verificar se usuário já está registrado
    if user_id in users:
        context.bot.send_message(chat_id=chat_id, text="Você já está registrado!")
    else:
        # Adicionar usuário ao dicionário
        users[user_id] = {'username': username, 'messages': 0}
        context.bot.send_message(chat_id=chat_id, text="Bem-vindo ao chatbot de OpenAI! Você pode enviar até {} mensagens antes de assinar o bot.".format(MESSAGE_LIMIT))

# Função para tratar comando /subscribe
def subscribe(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar se usuário já está registrado
    if user_id not in users:
        context.bot.send_message(chat_id=chat_id, text="Você precisa estar registrado para assinar o bot. Envie o comando /start para se registrar.")
    else:
        # Criar sessão de checkout no Stripe
        session = stripe.checkout.Session.create(
            customer_email=users[user_id]['username'],
            payment_method_types=['card'],
            line_items=[{
                'price': PLAN_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='http://localhost:5000/success.html',
            cancel_url='http://localhost:5000/cancel.html',
        )

        # Enviar mensagem com link de checkout
        keyboard = [[InlineKeyboardButton("Assinar", url=session.url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=chat_id, text="Clique no botão abaixo para assinar o bot:", reply_markup=reply_markup)

# Função para tratar mensagens
def echo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar se usuário já está registrado
    if user_id not in users:
        context.bot.send_message(chat_id=chat_id, text="Você precisa estar registrado para enviar mensagens. Envie o comando /start para se registrar.")
    else:
        # Verificar se usuário é assinante ou não
        if 'subscription' not in users[user_id]:
            # Verificar se usuário atingiu limite de mensagens
            if users[user_id]['messages'] >= MESSAGE_LIMIT:
                context.bot.send_message(chat_id=chat_id, text="Você atingiu o limite de mensagens gratuitas. Assine o bot para continuar usando.")
            else:
                 # Enviar mensagem para OpenAI e incrementar contador
                message = update.message.text
                response = openai.Completion.create(
                    model="text-davinci-003",
                    prompt=message,
                    max_tokens=1024,
                    n=1,
                    stop=None,
                    temperature=0.5,
                )
                context.bot.send_message(chat_id=chat_id, text=response.choices[0].text)
                users[user_id]['messages'] += 1
        else:
            # Enviar mensagem para OpenAI usando a API de assinante
            message = update.message.text
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=message,
                max_tokens=1024,
                n=1,
                stop=None,
                temperature=0.5,
            )
            context.bot.send_message(chat_id=chat_id, text=response.choices[0].text)

# Função para tratar callback de sucesso no Stripe
def success(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar se usuário já está registrado
    if user_id not in users:
        context.bot.send_message(chat_id=chat_id, text="Você precisa estar registrado para assinar o bot. Envie o comando /start para se registrar.")
    else:
        # Atualizar dicionário de usuários com informações de assinatura
        users[user_id]['subscription'] = {
            'status': 'active',
            'start_date': today,
        }
        context.bot.send_message(chat_id=chat_id, text="Assinatura realizada com sucesso!")

# Função para tratar callback de cancelamento no Stripe
def cancel(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar se usuário já está registrado
    if user_id not in users:
        context.bot.send_message(chat_id=chat_id, text="Você precisa estar registrado para cancelar a assinatura. Envie o comando /start para se registrar.")
    else:
        # Verificar se usuário é assinante ou não
        if 'subscription' not in users[user_id]:
            context.bot.send_message(chat_id=chat_id, text="Você não tem nenhuma assinatura ativa.")
        else:
            # Cancelar assinatura no Stripe
            subscription_id = users[user_id]['subscription']['id']
            subscription = stripe.Subscription.retrieve(subscription_id)
            subscription.delete()
            
            # Remover informações de assinatura do dicionário de usuários
            del users[user_id]['subscription']
            context.bot.send_message(chat_id=chat_id, text="Assinatura cancelada com sucesso!")

# Função principal para executar o bot
def main():
    # Criar objeto Updater e dispatcher
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Adicionar handlers para comandos e mensagens
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('subscribe', subscribe))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Adicionar handlers para callbacks do Stripe
    dispatcher.add_handler(CallbackQueryHandler(success, pattern='success'))
    dispatcher.add_handler(CallbackQueryHandler(cancel, pattern='cancel'))

    # Iniciar o bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
