Для развертывания выполнить:
НАСТРОЙКА БД:
1. Создать сеть Docker - sudo docker network create app-network
2. Создать том для MySQL - sudo docker volume create mysql_data
3. Скачать и запустить MySQL - sudo docker pull mysql:8.0.36 и sudo docker run -d --name flask-mysql --network app-network --restart always -e MYSQL_ROOT_PASSWORD=rootpassword -e MYSQL_USER=user -e MYSQL_PASSWORD=password -e MYSQL_DATABASE=mydb -p 3307:3306 -v mysql_data:/var/lib/mysql mysql:8.0.36
4. Создать таблицы, выполнить: sudo docker exec -it flask-mysql mysql -uuser -ppassword mydb (ЕСЛИ НЕТ БАЗЫ ДАННЫХ)
5. Выполнить слелующие команды SQL:
6.    CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, first_name VARCHAR(100) NOT NULL, last_name VARCHAR(100) NOT NULL, middle_name VARCHAR(100), password_hash VARCHAR(64) NOT NULL, email VARCHAR(255) UNIQUE NOT NULL, phone VARCHAR(20), birth_date DATE, registration_date DATETIME DEFAULT CURRENT_TIMESTAMP, avatar_url VARCHAR(500), position VARCHAR(255), access_rights VARCHAR(50) DEFAULT 'user') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
      CREATE TABLE user_images (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, filename VARCHAR(500) NOT NULL, upload_date DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
      CREATE TABLE user_action (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100), action VARCHAR(255), page VARCHAR(255), timestamp DATETIME DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
      INSERT INTO users (first_name, last_name, middle_name, password_hash, email, position, access_rights) VALUES ('Admin', 'Adminov', 'Adminovich', SHA2('admin123', 256), 'admin@example.com', 'Администратор', 'admin'); - добавления админа
      EXIT;
НАСТРОЙКА ПРИЛОЖЕНИЯ:
Скачать и запустить приложение - sudo docker pull levnerog228/pycharmprojects-app:latest и запустить sudo docker run -d --name myapp --network app-network -p 5001:5001 -e PYTHONPATH=/app -e FLASK_ENV=development -e MYSQL_HOST=flask-mysql -e MYSQL_USER=user -e MYSQL_PASSWORD=password -e MYSQL_DB=mydb -e SECRET_KEY=p98rnv4@sd! levnerog228/pycharmprojects-app:latest
Проверка работы 
sudo docker ps
sudo docker logs myapp
sudo docker exec myapp python -c "import pymysql; conn = pymysql.connect(host='flask-mysql', user='user', password='password', database='mydb'); print('Connection OK'); conn.close()"
