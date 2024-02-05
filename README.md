# Проектная работа «Резервное копирование» (API ВК)

## Описание проекта
Суть проекта: отправка фотографий из ВК на Яндекс диск по API. Вводные параметры: 1) ID пользователя ВК, 2) токен из [Полигона](https://yandex.ru/dev/disk/poligon/) для подключения к Яндекс Диску. При желании фотографии можно также отправить в Google Drive.

Ожидаемый результат: создание фотографий пользователя ВК в специальной папке (по умолчанию VK_Images) и вывод json файла с основной информацией о них (название фото и [его формат](https://dev.vk.com/ru/reference/objects/photo-sizes)). По умолчанию программа выводит 5 фотографий из ВК.

Проект выполнен на Python 3.12.1 в Visual Studio Code (64-bit, Windows 10). Код для запуска API расположен в файле API.py.

Перед запуском кода удостоверьтесь, что:
1. завели проект в Visual Studio Code или другом IDE
2. в папке с проектом размещен json файл client_secrets.json (в случае, если необходимо поработать с API Google Drive)

## Запуск программы
Для запуска кода необходимо только ввести: 
1) ID пользователя ВК в переменную  ```VK_ID```
2) токен из [Полигона](https://yandex.ru/dev/disk/poligon/) в переменную ```YD_token```.

```python
# VK_ID - ID пользователя в ВК
# YD_token - токен для входа в API Яндекс Диска
if __name__ == "__main__":
    VK_ID = 111111111
    YD_token = "y0_AgAAAAAAaAA1AAAAAaAAAAA1AAAAAAAAAAAAA-AA1AaaAa1AaAaaa_aAaA"
    APIClient = VK_APIClient(VK_ID, YD_token)
    json_result = APIClient.TOTAL_upload_VK_photo()
    print(' ', 'Полученный json файл: ', json_result, sep = "\n")
```

## Алгоритм работы программы
После запуска кода. Будут осуществлены следующие шаги:

### **Шаг 1. Запрос к пользователю на получение токена ВК** 

В этом случае мы просим его зайти по ссылке приложения PyVkontakte (ID веб-приложения ВК - 51849067). После перехода он копирует токен (access_token) из ссылки новой страницы и вводит его в поле ввода input (т.е. слева от надписи "Введите access_token:").


### **Шаг 2. Получение и обработка данных по фотографиям из ВК** 

Далее в случае корректного ввода токена написанния программа достанет фотографии из ВК методом [photos.get](https://dev.vk.com/ru/method/photos.get) и обработает их в том количестве, которое было указано в методе ```TOTAL_upload_VK_photo``` (по умолчению обрабатывается 5 фотографий).


### **Шаг 3. Отправка фотографий в Яндекс Диск** 

Далее отправляем фотографии методом POST на папку, заданную пользователем в методе ```TOTAL_upload_VK_photo``` (по умолчению фотографии отправляются на папку VK_Images). Результат - создание (при необходимости) и заполнение папки в Яндекс Диске.


### **Шаг 4. Задаем вопрос пользователю "Вы хотите загрузить фото из ВК на Google Drive?"** 

В случае положительного ответа переходим к шагу 5, а в случае отрицательного ответа - завершаем программу и выводим json файл с основной информацией о фотографиях (название фото и [его формат](https://dev.vk.com/ru/reference/objects/photo-sizes)).


### **Шаг 5. Запуск API Google Drive (необходим файл client_secrets.json в папке проекта)** 

Проводим подключение к API Google Drive (возможно предусмотренное переподключение по причине HttpAccessTokenRefreshError```*```). В случае успешного подключения к API программа проверит наличие папки в облачном хранилище (в случае необходимости она ее создаст) и перенаправит в нее фотографии из ВК. После успешного завршения шага будет выведен json файл с основной информацией о фотографиях.

```*``` - *В этом случае выведится сообщение " Ошибка доступа к API Google Drive (HttpAccessTokenRefreshError). Повторное подключение к API..." и начнется повторное подключениие программы к API Google Drive*

