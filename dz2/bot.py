import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import requests


API_TOKEN = "7489339867:AAFxUowoQkWTG0gNQ-ebHmixpnr4KTQBY4c"
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

users = {}

activity_varians = {
    'Бег': 10
}


class ProfileStates(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    water_goal = State()
    calorie_goal = State()


class FoodStates(StatesGroup):
    waiting_for_food_amount = State()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("""Добро пожаловать в бот, помогающий отследивать количество потраченных в день калорий. 
Начни с команды /set_profile для настройки профиля.""")


@dp.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state(ProfileStates.weight)


@dp.message(ProfileStates.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight=weight)
        await message.reply("Введите ваш рост (в см):")
        await state.set_state(ProfileStates.height)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для веса.")


@dp.message(ProfileStates.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height=height)
        await message.reply("Введите ваш возраст:")
        await state.set_state(ProfileStates.age)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для роста.")


@dp.message(ProfileStates.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await message.reply("Сколько минут активности у вас в день?")
        await state.set_state(ProfileStates.activity)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для возраста.")


@dp.message(ProfileStates.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await message.reply("В каком городе вы находитесь?")
        await state.set_state(ProfileStates.city)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для активности.")


@dp.message(ProfileStates.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    await state.update_data(city=city)
    await message.reply("Какая у вас цель по воде? Введите 0, если хотите рассчитать автоматически")
    await state.set_state(ProfileStates.water_goal)


@dp.message(ProfileStates.water_goal)
async def process_water_goal(message: Message, state: FSMContext):
    try:
        water_goal = int(message.text)
        await state.update_data(water_goal=water_goal)
        await message.reply("Какая у вас цель по калориям? Введите 0, если хотите рассчитать автоматически")
        await state.set_state(ProfileStates.calorie_goal)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для мл воды.")


@dp.message(ProfileStates.calorie_goal)
async def process_calorie_goal(message: Message, state: FSMContext):
    try:
        calorie_goal = int(message.text)
        await state.update_data(calorie_goal=calorie_goal)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для калорий.")

    data = await state.get_data()
    user_id = message.from_user.id

    water_goal = calculate_water_goal(data['weight'], data['activity'], data['city'], data['water_goal'])
    calorie_goal = calculate_calorie_goal(data['weight'], data['height'], data['age'], data['calorie_goal'])

    users[user_id] = {
        'weight': data['weight'],
        'height': data['height'],
        'age': data['age'],
        'activity': data['activity'],
        'city': data['city'],
        'water_goal': water_goal,
        'calorie_goal': calorie_goal,
        'logged_water': 0,
        'logged_calories': 0,
        'burned_calories': 0,
    }

    await message.reply(f"Профиль обновлен!\n\n"
                        f"Ваша дневная норма воды: {water_goal} мл\n"
                        f"Ваша дневная норма калорий: {calorie_goal} ккал")
    await state.clear()


def calculate_water_goal(weight, activity_minutes, city, water_goal):
    if water_goal > 0:
        return water_goal
    weather_water = 0
    if get_city_temperature(city) > 25:
        weather_water += 500
    return int(weight * 30 + (activity_minutes // 30) * 500 + weather_water)


def calculate_calorie_goal(weight, height, age, calorie_goal):
    if calorie_goal > 0:
        return calorie_goal
    calorie_goal = 10 * weight + 6.25 * height - 5 * age
    return int(calorie_goal)


@dp.message(Command("log_water"))
async def cmd_log_water(message: Message):
    user_id = message.from_user.id
    has_profile = check_user_has_profile(message, user_id)
    if not has_profile:
        return
    try:
        amount = int(message.text.split()[1])
        users[user_id]['logged_water'] += amount
        remaining = users[user_id]['water_goal'] - users[user_id]['logged_water']
        await message.reply(f"Записано: {amount} мл воды.\nОсталось: {remaining} мл до нормы.")
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, используйте формат команды: /log_water <количество_в_мл>")


@dp.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    has_profile = check_user_has_profile(message, user_id)
    if not has_profile:
        return
    try:
        product_name = ' '.join(message.text.split()[1:])
        food_info = get_food_info(product_name)
        if food_info:
            await state.update_data(food_calories=food_info['calories'])
            await message.reply(f"""{food_info['name']} — {food_info['calories']} ккал на 100 г. 
                                Сколько грамм вы съели?""")
            await state.set_state(FoodStates.waiting_for_food_amount)
        else:
            await message.reply("Не удалось найти информацию о продукте.")
    except IndexError:
        await message.reply("Пожалуйста, используйте формат команды: /log_food <название_продукта>")


@dp.message(FoodStates.waiting_for_food_amount)
async def process_food_amount(message: Message, state: FSMContext):
    try:
        grams = float(message.text)
        data = await state.get_data()
        calories_per_100g = data['food_calories']
        total_calories = (calories_per_100g * grams) / 100

        user_id = message.from_user.id
        users[user_id]['logged_calories'] += total_calories
        await message.reply(f"Записано: {total_calories:.1f} ккал.")
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректное количество в граммах.")

@dp.message(Command("log_workout"))
async def cmd_log_workout(message: Message):
    user_id = message.from_user.id
    has_profile = check_user_has_profile(message, user_id)
    if not has_profile:
        return
    try:
        parts = message.text.split()
        workout_type = parts[1]
        duration = int(parts[2])

        users[user_id]['burned_calories'] += activity_varians.get(workout_type, 5) * duration
        await message.reply(f"Записано: тренировка '{workout_type}' длительностью {duration} мин. "
                            f"Сожжено калорий: {users[user_id]['burned_calories']:.1f} ккал.")
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, используйте формат команды: /log_workout <тип> <время_в_минутах>")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    has_profile = check_user_has_profile(message, user_id)
    if not has_profile:
        return

    user_data = users[user_id]

    water_intake = user_data['logged_water']
    water_goal = user_data['water_goal']
    calories_consumed = user_data['logged_calories']
    calories_burned = user_data['burned_calories']
    calorie_goal = user_data['calorie_goal']

    await message.reply(f"Прогресс:\nВода:\n- Выпито: {water_intake} мл из {water_goal} мл.\n- Осталось: {water_goal-water_intake} мл.\n\nКалории:\n- Потреблено: {calories_consumed} ккал из {calorie_goal} ккал.",
                        parse_mode='Markdown')


def get_city_temperature(city):
    API_KEY = "b44b3fe6057829d2c1422f0d7b3f547b"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        temperature = data['main']['temp']
        return temperature
    else:
        return 0
    
def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
    return None
    
def check_user_has_profile(message, user_id):
    if user_id not in users:
        message.reply("Пожалуйста, сначала настройте профиль командой /set_profile")
        return False
    return True

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
