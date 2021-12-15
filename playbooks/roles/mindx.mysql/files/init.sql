CREATE DATABASE IF NOT EXISTS dataset_manager CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS label_manager   CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS license_manager CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS train_manager   CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS model_manager   CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS edge_manager    CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS task_manager    CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS image_manager   CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS data_manager    CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS cluster_manager CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS user_manager    CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS access_manager  CHARACTER SET utf8 COLLATE utf8_general_ci;

CREATE USER 'user_user'@'%'    IDENTIFIED BY "Huawei12#$";
CREATE USER 'edge_user'@'%'    IDENTIFIED BY "Huawei12#$";
CREATE USER 'dataset_user'@'%' IDENTIFIED BY "Huawei12#$";
CREATE USER 'license_user'@'%' IDENTIFIED BY "Huawei12#$";
CREATE USER 'train_user'@'%'   IDENTIFIED BY "Huawei12#$";
CREATE USER 'label_user'@'%'   IDENTIFIED BY "Huawei12#$";
CREATE USER 'model_user'@'%'   IDENTIFIED BY "Huawei12#$";
CREATE USER 'task_user'@'%'    IDENTIFIED BY "Huawei12#$";
CREATE USER 'image_user'@'%'   IDENTIFIED BY "Huawei12#$";
CREATE USER 'data_user'@'%'    IDENTIFIED BY "Huawei12#$";
CREATE USER 'cluster_user'@'%' IDENTIFIED BY "Huawei12#$";
CREATE USER 'access_user'@'%'  IDENTIFIED BY "Huawei12#$";

GRANT ALL PRIVILEGES ON *.* TO 'user_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'edge_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'dataset_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'license_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'train_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'label_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'model_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'task_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'image_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'data_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'cluster_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'access_user'@'%';