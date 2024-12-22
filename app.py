import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

API_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_current_temperature(city, key):
    params = {"q": city, "units": "metric", "appid": key}
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return data["main"]["temp"], None
    elif response.status_code == 401:
        return None, '{"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}'
    else:
        return None, f"Ошибка при запросе температуры для {city}: {response.status_code}"

def is_temperature_anomalous(city_data, temp):
    temp_mean = city_data['temperature'].mean()
    temp_std = city_data['temperature'].std()
    lower_bound = temp_mean - 2 * temp_std
    upper_bound = temp_mean + 2 * temp_std
    
    if temp < lower_bound or temp > upper_bound:
        return True, lower_bound, upper_bound
    return False, lower_bound, upper_bound


def main():
    st.title('Приложение: Анализ Погоды')

    st.subheader('Загрузите файл')
    uploaded_file = st.file_uploader('Загрузите файл CSV c историческими данными', type='csv')

    api_key = st.text_input('Введите ваш OpenWeatherMap API Key:')
    
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        city_selection = st.selectbox('Выберите город:', options=data['city'].unique())
        city_data = data[data['city'] == city_selection]
        
        st.write(f'Данные для города: {city_selection}')
        st.dataframe(city_data)
        st.subheader('Описательная статистика по историческим данным')
        st.write(city_data.describe())

        st.subheader('Временной ряд температур')
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.plot(pd.to_datetime(city_data['timestamp']), city_data['temperature'], label='Температура')
        ax.set_title(f'Временной ряд температур для {city_selection}')
        ax.set_xlabel('Дата')
        ax.set_ylabel('Температура')
        plt.xticks(rotation=45)
        st.pyplot(fig)

        st.subheader('Сезонные профили')
        city_data['month'] = pd.to_datetime(city_data['timestamp']).dt.month
        seasonal_profile = city_data.groupby('month')['temperature'].agg(['mean', 'std']).reset_index()
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.bar(seasonal_profile['month'], seasonal_profile['mean'], yerr=seasonal_profile['std'], label='Средняя температура', alpha=0.7, capsize=5)
        ax.set_title(f'Сезонные профили температуры для {city_selection}')
        ax.set_xlabel('Месяц')
        ax.set_ylabel('Температура')
        st.pyplot(fig)

        curr_temp, err = get_current_temperature(city_selection, api_key)
        if err is not None:
            st.error(err)
        elif curr_temp is not None:
            st.write(f'Текущая температура в городе {city_selection}: {curr_temp}')

            anomalous, lower_bound, upper_bound = is_temperature_anomalous(city_data, curr_temp)
            if anomalous:
                st.error(f'Температура {curr_temp} градусов по Цельсию является аномальной. Нормальный диапазон: {lower_bound:.2f} : {upper_bound:.2f}')
            else:
                st.success(f'Температура {curr_temp} градусов по Цельсию является нормальной. Нормальный диапазон: {lower_bound:.2f} : {upper_bound:.2f}')

if __name__ == '__main__':
    main()