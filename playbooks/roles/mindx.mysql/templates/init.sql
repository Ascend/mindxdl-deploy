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

CREATE USER 'user_user'@'%'    IDENTIFIED BY "{{pwd}}";
CREATE USER 'edge_user'@'%'    IDENTIFIED BY "{{pwd}}";
CREATE USER 'dataset_user'@'%' IDENTIFIED BY "{{pwd}}";
CREATE USER 'license_user'@'%' IDENTIFIED BY "{{pwd}}";
CREATE USER 'train_user'@'%'   IDENTIFIED BY "{{pwd}}";
CREATE USER 'label_user'@'%'   IDENTIFIED BY "{{pwd}}";
CREATE USER 'model_user'@'%'   IDENTIFIED BY "{{pwd}}";
CREATE USER 'task_user'@'%'    IDENTIFIED BY "{{pwd}}";
CREATE USER 'image_user'@'%'   IDENTIFIED BY "{{pwd}}";
CREATE USER 'data_user'@'%'    IDENTIFIED BY "{{pwd}}";
CREATE USER 'cluster_user'@'%' IDENTIFIED BY "{{pwd}}";
CREATE USER 'access_user'@'%'  IDENTIFIED BY "{{pwd}}";

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

USE image_manager;
CREATE TABLE IF NOT EXISTS image_configs(
    ID BIGINT AUTO_INCREMENT,
    UserID BIGINT NOT NULL DEFAULT 0,
    GroupID BIGINT NOT NULL DEFAULT 0,
    ImageName VARCHAR(256),
    ImageTag VARCHAR(32),
    ImageSize DOUBLE NOT NULL,
    HarborPath VARCHAR(256),
    Prefabricated tinyint(1) NOT NULL DEFAULT 1,
    ImageArch VARCHAR(32) NOT NULL DEFAULT 'noarch',
    CreateTime DATETIME NOT NULL,
    Status tinyint(1) NOT NULL DEFAULT 0,
    ExtraParam VARCHAR(256) DEFAULT '',
    PRIMARY KEY ( ID ),
    UNIQUE (HarborPath)
)ENGINE=InnoDB DEFAULT CHARSET=utf8;
