from __future__ import print_function

import os
import time
import json
import httplib2
import requests

from tqdm import tqdm
from datetime import datetime
from oauth2client import tools
from oauth2client import client
from apiclient import discovery
from urllib.parse import urlencode
from oauth2client.file import Storage
from oauth2client.client import HttpAccessTokenRefreshError

# Построение класса для работы с общими методами
class BaseMethod:

    ###### ОБЩИЕ МЕТОДЫ ######
    # Выведение ровного неоднострочного сообщения (message),
    # написанного при тройных кавычках (""")
    def BM_write_msg(self, message):
        print(*[row.lstrip() for row in message.splitlines()], sep = "\n")

    # Получение отклика запроса в рамках:
    # 1) метода (method), 2) URL (url), 3) параметров запроса (params),
    # 4) заголовков запроса (headers), 5) файлов (files), 6) данных (data)
    def BM_get_response(self, method, url, params = None, headers = None,
                           files = None, data = None):
        retry_attempts = 3
        retry_delay = 30
        for _ in range(retry_attempts):
            try:
                response = requests.request(method, url, params = params,
                                            headers = headers, 
                                            files = files, data = data,
                                            timeout = retry_delay)
                return response
            except requests.exceptions.ConnectTimeout:
                continue
        return None

    # Построение словаря с весами на основе списка weight_params
    # Пример: weight_params = ["w", "z"] => weight_dict = {"w": 2,"z": 1}
    def BM_get_weight_dict(self, weight_params):
        weight_dict = dict(zip(weight_params,
                                range(len(weight_params), 0, -1)))
        return weight_dict

    # Подсчет повторяющихся значений str_name в списке словарей dict_list
    def BM_find_repeats(self, dict_list, str_name):
        val_l = [my_dict.get(str_name) for my_dict in dict_list]
        repeat_val_l = [i for i in val_l if val_l.count(i) >= 2]
        return repeat_val_l

    # Получение нового словаря с конкретной связкой ключ-значение
    # по ключам my_keys на основе первоначального словаря my_dict
    def BM_get_dict_part(self, my_dict, my_keys):
        return {key: val for key, val in my_dict.items() if key in my_keys}

    # Установка параметров для работы с полоской загрузки библиотеки tqdm
    def BM_set_bar_format(self):
        return "{desc:<10}{percentage:10.2f}%|{bar:50}{r_bar}"
    
    # Задание параметров для выведения полоски загрузки
    # в разрезе одноцикличной операции. desc - описание процесса,
    # который будет находиться рядом с прогресс-баром
    def BM_set_one_loop_bar(self, desc):
        return tqdm(range(1), desc, bar_format = self.BM_set_bar_format())

    # Установка параметров для выведения полоски загрузки в
    # разрезе многоцикличной операции. loop_values - набор
    # значений, задействованных в самом цикле
    def BM_set_n_loop_bar(self, loop_values):
        return tqdm(loop_values, bar_format = self.BM_set_bar_format())
    
    # Выведение описания процесса, находящегося рядом
    # с полоской загрузки. Параметры:
    # my_pbar - объект tqdm, n_loop - текущее значение цикла,
    # total - общее кол-во оборотов в цикле, status - статус
    def BM_set_loop_desc(self, my_pbar, n_loop, total, status,
                         start_text = "фотографий из ВК в обработке",
                         end_text = "фотографий из ВК обработано"):
        if status == "start":
            my_pbar.set_description(f"{n_loop} из {total} {start_text}")
        elif status == "end":
            my_pbar.set_description(f"{n_loop} из {total} {end_text}")

# Построение класса для работы со специфическими методами в
# разрезе API ВК, Яндекс Диска и (при желании) Google Drive
class VK_APIClient(BaseMethod):

    # Инициализация начальных значений атрибутов класса
    # VK_user_id - ID пользователя ВК
    # token_YD - токен для доступа к API Яндекс Диска
    def __init__(self, VK_user_id, token_YD,
                 version = '5.131', APP_VK_ID = "51849067"):
        self.VK_user_id = VK_user_id
        self.token_YD = token_YD
        self.version = version
        self.APP_VK_ID = APP_VK_ID
    
    ###### МЕТОДЫ ДЛЯ РАБОТЫ С API ВК ######
    def VK_build_oauth_url(self):
        base_url = "https://oauth.vk.com/authorize"
        keys_l = ["client_id", "display", "redirect_uri",
                  "scope", "response_type", "v", "state"]
        vals_l = [self.APP_VK_ID, "page", "https://example.com/callback",
                  "friends,photos", "token", self.version, "123456"]
        dict_params = dict(zip(keys_l, vals_l))
        return f"{base_url}?" + urlencode(dict_params, safe = ",:/")

    # Выведение сообщения о вводе пользователем токена ВК
    def VK_write_msg_get_token(self):
        VK_oauth_url = self.VK_build_oauth_url()
        message = f"""\
            ======================================
            ПОЛУЧЕНИЕ ТОКЕНА ДЛЯ РАБОТЫ С ВК
            ======================================
            Просим вас произвести следующие последовательные действия:
            Шаг 1. Зарегистрируйтесь и/или войдите в личный кабинет ВК
            Шаг 2. Введите в браузере следующую ссылку: {VK_oauth_url}
            Шаг 3. Нажмите кнопку "Продолжить"
            Шаг 4. Скопируйте токен (access_token) из ссылки новой страницы
            Шаг 5. Введите скопированный токен в нижнее поле"""
        return self.BM_write_msg(message)
    
    # Взятие токена ВК после ввода пользователем ответа
    def VK_get_token(self):
        self.VK_write_msg_get_token()
        token = input("Введите access_token: ")
        return token

    # Выведение базового URL при работе с API VK
    # вместе с названием API метода (api_method)
    def VK_build_API_url(self, api_method):
        return f"{'https://api.vk.com/method'}/{api_method}"

    # Выведение сообщения о начале работы с фотографиями из ВК
    def VK_write_msg_get_photos(self):
        message = """\
            ======================================
            ПОЛУЧЕНИЕ ДАННЫХ ПО ФОТОГРАФИЯМ ИЗ ВК
            ======================================"""
        return self.BM_write_msg(message)

    # Выведение данных по фотографиям
    # пользователя VK API методом photos.get
    def VK_get_profile_photos(self):
        keys_l = ["access_token", "v", "owner_id", 
                  "album_id", "extended"]
        vals_l = [self.VK_get_token(), self.version, 
                  self.VK_user_id, "profile", 1]
        dict_params = dict(zip(keys_l, vals_l))
        vk_url = self.VK_build_API_url("photos.get")
        self.VK_write_msg_get_photos()
        pbar = self.BM_set_one_loop_bar("Вывод информации" \
                                        " по всем фотографиям")
        for _ in pbar:
            response = self.BM_get_response("GET", vk_url, dict_params)
        return response.json()
    
    # Получение основной информации о конкретной
    # фотографии из общего набора (имя файла, дата
    # публикации, кол-ло лайков)
    def VK_get_album_general_info(self, album_id):
        photo_likes = album_id.get("likes").get("count")
        file_name = str(photo_likes) + ".jpg"
        date = album_id.get("date")
        time_format = "%Y-%m-%d %H:%M:%S"
        publish_date = datetime.fromtimestamp(date).strftime(time_format)
        return dict(zip(["file_name", "likes", "date"],
                        [file_name, photo_likes, publish_date]))

    # Выведение словаря weight_dict с весами. Больший размер 
    # фотографии = больший вес. Описание всех форматов фотографий
    # представлен в официальной документации ВК:
    # https://dev.vk.com/ru/reference/objects/photo-sizes
    # В данном случае выводимый словарь weight_dict имеет
    # следуюший вид: weight_dict = {"w": 10, "z": 9, "y": 8,
    # "x": 7, "r": 6, "q": 5, "p": 4, "o": 3, "m": 2, "s": 1}
    def VK_get_weight_dict_l(self):
        return self.BM_get_weight_dict(["w", "z", "y", "x", "r", 
                                        "q", "p", "o", "m", "s"])

    # Выявление крупнейших версий фотографий в рамках списка sizes_info_l,
    # содержащего данные по всем форматам конкретной фотографии.
    # Критерий поиска - веса, содержащиеся в словаре weight_dict
    def VK_get_max_photo(self, sizes_info_l, weight_dict):
        size_url_l = [{"size": d.get("type"), 
                       "url": d.get("url")} for d in sizes_info_l]
        weight_l = [weight_dict.get(d.get("size")) for d in size_url_l]
        return size_url_l[weight_l.index(max(weight_l))]

    # Получение списка photo_l с основными данными по фотографиям
    # (имя файла, дата публикации, кол-ло лайков, макс. формат фото, URL)
    # max_photo - макс. кол-во фотографий для обработки
    def VK_get_photo_l(self, max_photo):
        data = self.VK_get_profile_photos()
        if "error" not in data:
            photo_l = []
            weight_dict = self.VK_get_weight_dict_l()
            album_id_l = data.get("response").get("items")[:max_photo]
            pbar = self.BM_set_n_loop_bar(range(len(album_id_l)))
            for n, album_id in zip(pbar, album_id_l):
                sizes = album_id.get("sizes")
                self.BM_set_loop_desc(pbar, n + 1, len(album_id_l), 'start')
                data_dict = self.VK_get_album_general_info(album_id)
                data_dict.update(self.VK_get_max_photo(sizes, weight_dict))
                self.BM_set_loop_desc(pbar, n + 1, len(album_id_l), 'end')
                photo_l.append(data_dict)
            return photo_l
        else:
            return data

    ###### МЕТОДЫ ДЛЯ РАБОТЫ С API Яндекс Диска ######
    # Выведение сообщения о начале отправки фотографий в Яндекс Диск
    def YD_write_msg_send_photos(self):
        message = f"""\
            ======================================
            ОТПРАВКА ФОТОГРАФИЙ В ЯНДЕКС ДИСК
            ======================================"""
        return self.BM_write_msg(message)

    # Выведение базового URL с указанием необходимого
    # API запроса (api_request) при работе с Яндекс Диском
    def YD_build_API_url(self, api_request):
        url_yadisk = "https://cloud-api.yandex.net"
        return f"{url_yadisk}/{api_request}"

    # Получение заголовка запроса для работы с API Яндекс Диска
    def YD_get_header_url(self):
        return {"Authorization": f"OAuth {self.token_YD}"}
  
    # Построение запроса в рамках API Яндекс Диска
    # method - метод осуществления запроса
    # api_request - API запрос Яндекс Диска
    # dict_params - параметры запроса
    def YD_build_request(self, method, api_request, dict_params):
        return self.BM_get_response(method,
                                       self.YD_build_API_url(api_request),
                                       dict_params, self.YD_get_header_url())

    # Выведение параметров запроса c учетом наличия повторов в лайках
    # photo_dict - словарь с данными по конкретной фотографии из ВК
    # path - путь, по которому хотим отправить фотографию из ВК (в
    # данном случае это название папки)
    # likes_repeat - показатель наличия/отсутствия повторяющихся лайков
    # photo_name - текущее/изменившееся имя фотографии
    def YD_get_params_url(self, photo_dict, path, likes_repeat = "No"):
        if likes_repeat == "Yes":
            replace_jpg = photo_dict.get('file_name').replace('.jpg','')
            photo_name = f"{replace_jpg} {photo_dict.get('date')}.jpg"
        else:
            photo_name = photo_dict.get("file_name")
        return photo_name, {"path": f"disk:/{path}/{photo_name}",
                            "url": photo_dict.get("url")}

    # Построение запроса методом POST для отправки фото из ВК
    # photo_l - лист словарей с данными по фотографиям из ВК
    # repeat_likes_l - список повторяющихся лайков по фотографиям
    # path - путь, по которому хотим отправить фото из ВК
    # photo_dict - словарь с данными по конкретной фотографии из ВК
    # Результат - учет повторяющихся лайков и обновленный
    # список словарей с фотографиями (new_photo_l)
    def YD_do_post_response(self, photo_l, repeat_likes_l, path):
        new_photo_l = []
        pbar = self.BM_set_n_loop_bar(range(len(photo_l)))
        for n, photo_dict in zip(pbar, photo_l):
            self.BM_set_loop_desc(pbar, n + 1, len(photo_l), 'start')
            if photo_dict.get("likes") in repeat_likes_l:
                name, params = self.YD_get_params_url(photo_dict, path, "Yes")
                photo_dict.update({"file_name": name})
            else:
                _, params = self.YD_get_params_url(photo_dict, path)
            self.YD_build_request("POST", "v1/disk/resources/upload", params)
            new_photo_l.append(photo_dict)
            self.BM_set_loop_desc(pbar, n + 1, len(photo_l), 'end')
        return new_photo_l

    # Отправка фотографий в Яндекс Диск по токену из Полигона
    # path - путь, по которому хотим отправить фото из ВК
    # max_photo - макс. кол-во фотографий для обработки
    # Результат - создание (при необходимости) и заполнение 
    # папки в Яндекс Диске
    def YD_send_photos(self, path, max_photo):
        photo_l = self.VK_get_photo_l(max_photo)
        params = {"path": path}
        api_request = "v1/disk/resources"
        if "error" not in photo_l:
            self.YD_write_msg_send_photos()
            repeat_likes_l = self.BM_find_repeats(photo_l, "likes")
            folder_check = self.YD_build_request("GET", api_request, params)
            if 200 <= folder_check.status_code < 300:
                return self.YD_do_post_response(photo_l, repeat_likes_l, path)
            else:
                self.YD_build_request("PUT", api_request, params)
                return self.YD_do_post_response(photo_l, repeat_likes_l, path)
        else:
            return photo_l

    ###### МЕТОДЫ ДЛЯ РАБОТЫ С API Google Drive ######
    # Для работы с API Google Drive необходимо:
    # 1) завести json файл, содержащий данные 
    # клиентского приложения (client_secret.json)
    # 2) поместить файл client_secret.json в папку 
    # с проектом, в котором хранится текущий файл (API.py)
    # 3) При запуске метода GD_get_credentials необходимо указать
    # название файла с данными приложения (client_secret.json)

    # Проверка флагов
    def GD_check_flags(self):
        try:
            import argparse
            parents = [tools.argparser]
            flags = argparse.ArgumentParser(parents = parents).parse_args()
        except ImportError:
            flags = None
        return flags
    
    # Формирование пути для создания json файла с полномочиями
    # (drive-python-quickstart.json). В нем будет храниться,
    # в частности, токен для подключения к API Google Drive
    def GD_get_credential_path(self):
        flags = self.GD_check_flags()
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        return flags, os.path.join(credential_dir, 
                                   'drive-python-quickstart.json')

    # Формирование json файла с полномочиями для авторизации через API
    # CLIENT_SECRET_FILE - имя файла с данными приложения
    # SCOPES - список прав доступа, которые необходимо получить
    # APPLICATION_NAME - имя приложения
    def GD_get_credentials(self, CLIENT_SECRET_FILE = 'client_secrets.json',
                           SCOPES = ["https://www.googleapis.com/auth/drive"],
                           APPLICATION_NAME = 'drive'):
        flags, credential_path = self.GD_get_credential_path()
        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else:
                credentials = tools.run(flow, store)
        return credentials, credential_path
    
    # Получение токена для подключения к API Google Drive
    # credential_path - путь к json файлу с полномочиями (drive-
    # python-quickstart.json)
    def GD_get_access_token(self, credential_path):
        with open(credential_path) as file:
            access_token = json.load(file).get('access_token')
        return access_token
    
    # Выведение сообщения о процессе получения
    # прав доступа к API Google Drive
    def GD_write_msg_api_connect(self):
        message = f"""\
            ======================================
            ПОЛУЧЕНИЕ ПРАВ ДОСТУПА К API GOOGLE DRIVE
            ======================================"""
        return self.BM_write_msg(message)
    
    # Соединение к сервису, предоставляемому Google в виде API
    # service - объект, предоставляющий доступ к API Google Drive
    def GD_connect_wtih_service(self):
      self.GD_write_msg_api_connect()
      pbar = self.BM_set_one_loop_bar("Подключение к API Google Drive")
      for _ in pbar:
        credentials, credential_path = self.GD_get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('drive', 'v3', http=http)
      return service, self.GD_get_access_token(credential_path)
    
    # Получение информации о папке с названием file_name
    # service - объект, предоставляющий доступ к API Google Drive
    # file_name - название папки
    # pageSize - количество словарей с информацией о конкретном 
    # файле из Google Drive в виде словаря (фото, папка и т.д.)
    # Результат - словарь с информацией о конкретной папке (если она есть)
    def GD_get_file_info(self, service, file_name, pageSize = 1000):
        fields = "nextPageToken, files(id, name, mimeType, parents,\
            createdTime, permissions, quotaBytesUsed, trashed)"
        query = f"name contains '{file_name}' and trashed = {False}"
        return service.files().list(pageSize = pageSize,
                                    fields = fields, q = query).execute()

    # Построение ссылки для работы с API Google Drive
    # url_part - часть ссылки, необходимая для работы с API Google Drive
    def GD_create_url(self, url_part):
        return f'https://www.googleapis.com/{url_part}'
    
    # Выведение заголовков запроса на создание папки (в случае отсутствия)
    # access_token - токен для подключения к API Google Drive
    def GD_get_headers(self, access_token):
        return {'Authorization': 'Bearer {}'.format(access_token), 
                'Content-Type': 'application/json'}
    
    # Выведение данных для создания папки (в случае отсутствия)
    # folder_name - название папки
    # parent_folder_id - id родительской папки
    def GD_get_data(self, folder_name, parent_folder_id):
        return {'name': folder_name,'parents': [parent_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'}

    # Создание папки (в случае отсутствия)
    # access_token - токен для подключения к API Google Drive
    # folder_name - название папки
    # Результат - создание папки в Google Drive
    def GD_create_folder(self, access_token, folder_name):
        headers = self.GD_get_headers(access_token)
        data = self.GD_get_data(folder_name, None)
        self.BM_get_response('POST', self.GD_create_url('drive/v3/files'),
                                headers = headers, data = json.dumps(data))

    # Проверка наличия папки и ее создание (в случае необходимости)
    # Учет токена (access_token) для подключения к API
    # f_name - название папки
    def GD_check_and_get_folder_info(self, f_name):
        retry_attempts = 3
        retry_delay = 30
        for _ in range(retry_attempts):
            try:
                service, access_token = self.GD_connect_wtih_service()
                info = self.GD_get_file_info(service, f_name).get('files')
                if len(info) == 0:
                    self.GD_create_folder(access_token, f_name)
                    data = self.GD_get_file_info(service, f_name).get('files')
                elif len(info) >= 1:
                    data = info
                return data[0], access_token
            except HttpAccessTokenRefreshError:
                err_name = "HttpAccessTokenRefreshError"
                print(f'Ошибка доступа к API Google Drive ({err_name})',
                      'Повторное подключение к API...', sep = "\n")
                time.sleep(retry_delay)
                continue
        return None, None

    # Вывод параметров запроса на размещение фото из ВК в Google Drive
    # photo_title - название фотографии
    # folder_id - id папки, в которую планируем разместить фотографию
    def GD_get_params(self, photo_title, folder_id):
        return {"title": photo_title, "parents": [{"id": folder_id}]}
    
    # Вывод данных для создания фотографии в Google Drive
    # params - параметры запроса
    # url_file_content - контент ссылки на файл фотографии
    def GD_get_files(self, params, url_file_content):
        return {"data": ("metadata", json.dumps(params), 
                         "application/json; charset=UTF-8"),
                         "file": url_file_content}
    
    # Построение URL для отправки фотографий в Google Drive
    # методом POST-запроса
    def GD_create_post_url(self):
        post_url = self.GD_create_url('upload/drive/v2/files')
        query_part = "?uploadType=multipart"
        return f"{post_url}{query_part}"

    # Выведение сообщения о начале отправки фотографий в Google Drive
    def GD_write_msg_send_photos(self):
        message = f"""\
            ======================================
            ОТПРАВКА ФОТОГРАФИЙ В GOOGLE DRIVE
            ======================================"""
        return self.BM_write_msg(message)

    # Загрузка фотографий из ВК на папку из Google Drive
    # photo_title_l - список с названиями фотографий
    # url_l - список со ссылками на фотографии
    # folder_name - название папки, в которую будут загружены фотографии
    # Результат - размещение фотографий в конкретную папку из Google Drive
    def GD_upload_photo_to_folder(self, photo_title_l, url_l, folder_name):
        folder_info, token = self.GD_check_and_get_folder_info(folder_name)
        self.GD_write_msg_send_photos()
        headers = {'Authorization': 'Bearer {}'.format(token)}
        pbar = self.BM_set_n_loop_bar(range(len(url_l)))
        for n, photo_title, url in zip(pbar, photo_title_l, url_l):
            self.BM_set_loop_desc(pbar, n + 1, len(url_l), 'start')
            params = self.GD_get_params(photo_title, folder_info.get('id'))
            url_file_content = self.BM_get_response('GET', url).content
            files = self.GD_get_files(params, url_file_content)
            self.BM_get_response('POST', self.GD_create_post_url(),
                                    headers = headers, files = files)
            self.BM_set_loop_desc(pbar, n + 1, len(url_l), 'end')

    ###### РЕАЛИЗАЦИЯ ВСЕХ НАПИСАННЫХ ВЫШЕ МЕТОДОВ ######
    # Вывод сообщения с вопросом пользователю 
    # относительно загрузки фото на Google Drive
    def TOTAL_write_msg_GD_question(self):
        return "Вы хотите загрузить фото из ВК на Google Drive"\
            " (Y - да/N или что-то еще - нет): "

    # Реализовываем все написанные выше методы для работы с фотографиями из ВК
    # По умолчанию создается папка VK_Images (folder)
    # По умолчанию обрабатываются данные по 5 фотографиям (max_photo)
    def TOTAL_upload_VK_photo(self, folder = 'VK_Images', max_photo = 5):
        photos_data = self.YD_send_photos(folder, max_photo)
        if "error" not in photos_data:
            answer = input(self.TOTAL_write_msg_GD_question())
            if answer == 'Y':
                name_l = [d.get('file_name') for d in photos_data]
                url_l = [d.get('url') for d in photos_data]
                self.GD_upload_photo_to_folder(name_l, url_l, folder)
            return [self.BM_get_dict_part(d, ["file_name",
                                              "size"]) for d in photos_data]
        else:
            return photos_data

# Проверка работы методов класса VK_APIClient
# VK_ID - ID пользователя в ВК
# YD_token - токен для входа в API Яндекс Диска
if __name__ == "__main__":
    VK_ID = 111111111
    YD_token = "y0_AgAAAAAAaAA1AAAAAaAAAAA1AAAAAAAAAAAAA-AA1AaaAa1AaAaaa_aAaA"
    APIClient = VK_APIClient(VK_ID, YD_token)
    json_result = APIClient.TOTAL_upload_VK_photo()
    print(' ', 'Полученный json файл: ', json_result, sep = "\n")