-- GuardianTix Database Backup
SET FOREIGN_KEY_CHECKS=0;

CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'user',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=latin1;

INSERT INTO users (id, username, email, password_hash, role, created_at) VALUES
(9, 'System Admin', 'admin@guardiantix.com', 'scrypt:32768:8:1$oAJ4JCVm1ZzuIS4s$d5be1e48a12ec8e2327a9290289902595d58cc8d0079cf4f9b4e6e24569f8a29b07aa4d1768c29d86281a17c43eb0fb1116bbda062d9df7f2619309c8f5a0c35', 'admin', 2025-10-20 12:49:24),
(11, 'cake', 'cake@gmail.com', 'scrypt:32768:8:1$2hFx7lUyfXDkrSfp$35b47b2749994f83a15591ee56eae3f73b87c8c60a400d9cdf4bcf631912e49fa8675db97e368875fea08ed83c8332d29ea85cc3aa87b1b9fbf3b79e82693cf4', 'user', 2025-10-20 12:53:56),
(12, 'loe', 'loe@gmail.com', 'scrypt:32768:8:1$TPYRqS3rWOPeZMjC$5a18b517eb93f1a8a0ec3a97cf6e3d04858cbc2adea68e8fe04c8e6713160b0fb327a0dc92dea84b0fb98703173635581053c3088ea4f7e750651360ad179e4c', 'user', 2025-11-02 19:47:24);

CREATE TABLE `events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `event_date` date NOT NULL,
  `location` varchar(255) NOT NULL,
  `status` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=latin1;

INSERT INTO events (id, name, event_date, location, status, created_at) VALUES
(2, 'Reality Club', 2025-10-31, 'pollux', 'Active', 2025-10-20 12:55:22);

CREATE TABLE `tickets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` int NOT NULL,
  `type_name` varchar(100) NOT NULL,
  `price` int NOT NULL,
  `quota` int NOT NULL,
  `sold` int NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `available` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `tickets_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=latin1;

INSERT INTO tickets (id, event_id, type_name, price, quota, sold, created_at, available) VALUES
(3, 2, 'VIP', 1000000, 30, 4, 2025-10-20 12:55:37, 29),
(4, 2, 'Regular', 100000, 50, 8, 2025-10-24 08:47:46, 50);

CREATE TABLE `payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `event_id` int DEFAULT NULL,
  `payment_method` varchar(50) DEFAULT 'VA',
  `va_number` varchar(100) DEFAULT NULL,
  `amount` int DEFAULT NULL,
  `status` varchar(50) DEFAULT 'pending',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NULL DEFAULT NULL,
  `paid_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `payments_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO payments (id, user_id, event_id, payment_method, va_number, amount, status, created_at, expires_at, paid_at) VALUES
(2, 12, 2, 'VA', '880000126398', 5000, 'pending', 2025-10-24 02:06:38, 2025-10-25 02:06:38, NULL),
(4, 12, 2, 'VA', '880000120428', 5000, 'pending', 2025-10-24 06:00:28, 2025-10-25 06:00:28, NULL),
(5, 12, 2, 'VA', '880000126073', 5000, 'pending', 2025-10-24 07:34:33, 2025-10-25 07:34:33, NULL),
(6, 11, 2, 'VA', '880000118403', 1000000, 'pending', 2025-10-24 08:13:23, 2025-10-25 08:13:23, NULL),
(7, 11, 2, 'VA', '880000118417', 1000000, 'pending', 2025-10-24 08:13:37, 2025-10-25 08:13:37, NULL),
(8, 11, 2, 'VA', '880000118551', 1000000, 'pending', 2025-10-24 08:15:51, 2025-10-25 08:15:51, NULL),
(9, 11, 2, 'VA', '880000118563', 1000000, 'pending', 2025-10-24 08:16:03, 2025-10-25 08:16:03, NULL),
(10, 11, 2, 'VA', '880000119715', 1000000, 'pending', 2025-10-24 08:35:15, 2025-10-25 08:35:15, NULL),
(11, 11, 2, 'VA', '880000110415', 1000000, 'pending', 2025-10-24 08:46:55, 2025-10-25 08:46:55, NULL),
(12, 11, 2, 'VA', '880000110502', 100000, 'pending', 2025-10-24 08:48:22, 2025-10-25 08:48:22, NULL),
(13, 11, 2, 'VA', '880000110985', 100000, 'paid', 2025-10-24 08:56:25, 2025-10-25 08:56:25, NULL),
(14, 11, 2, 'VA', '880000111714', 100000, 'paid', 2025-10-24 09:08:34, 2025-10-25 09:08:34, NULL),
(15, 11, 2, 'VA', '880000111735', 1000000, 'paid', 2025-10-24 09:08:55, 2025-10-25 09:08:55, NULL),
(16, 11, 2, 'VA', '880000111956', 100000, 'paid', 2025-10-24 09:12:36, 2025-10-25 09:12:36, NULL),
(17, 11, 2, 'VA', '880000112681', 1000000, 'paid', 2025-10-24 09:24:41, 2025-10-25 09:24:41, NULL),
(19, 11, 2, 'VA', '880000111171', 100000, 'paid', 2025-11-06 13:39:31, 2025-11-07 13:39:31, NULL),
(20, 11, 2, 'VA', '880000118677', 100000, 'paid', 2025-11-06 15:44:37, 2025-11-07 15:44:37, NULL),
(22, 11, 2, 'VA', '880000119093', 1000000, 'pending', 2025-11-06 15:51:33, 2025-11-07 15:51:33, NULL),
(23, 11, 2, 'VA', '880000119398', 100000, 'paid', 2025-11-06 15:56:38, 2025-11-07 15:56:38, NULL),
(25, 11, 2, 'BCA', '880000111373', 1000000, 'paid', 2025-11-06 16:29:33, 2025-11-07 16:29:33, NULL),
(26, 11, 2, 'BCA', '880000111421', 100000, 'paid', 2025-11-06 16:30:21, 2025-11-07 16:30:21, NULL),
(28, 11, 2, 'BCA', '880000111119', 100000, 'paid', 2025-11-06 21:58:39, 2025-11-07 21:58:39, NULL),
(29, 11, 2, 'BCA', '880000112254', 100000, 'paid', 2025-11-06 22:17:34, 2025-11-07 22:17:34, NULL),
(30, 11, 2, 'BCA', '880000113041', 100000, 'paid', 2025-11-06 22:30:41, 2025-11-07 22:30:41, NULL);

CREATE TABLE `orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `event_id` int NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `status` enum('pending','paid','cancelled','expired') DEFAULT 'pending',
  `order_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `customer_name` varchar(255) NOT NULL,
  `customer_email` varchar(255) NOT NULL,
  `customer_phone` varchar(20) DEFAULT NULL,
  `payment_status` varchar(50) DEFAULT 'pending',
  `payment_id` int DEFAULT NULL,
  `ticket_details` text,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `orders_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO orders (id, user_id, event_id, total_amount, status, order_date, customer_name, customer_email, customer_phone, payment_status, payment_id, ticket_details) VALUES
(2, 12, 2, 5000.00, 'pending', 2025-10-24 02:06:38, 'loe', 'loe@gmail.com', NULL, 'pending', 2, 'Regular x1'),
(4, 12, 2, 5000.00, 'pending', 2025-10-24 06:00:28, 'loe', 'loe@gmail.com', NULL, 'pending', 4, 'Regular x1'),
(5, 12, 2, 5000.00, 'pending', 2025-10-24 07:34:33, 'loe', 'loe@gmail.com', NULL, 'cancelled', 5, 'Regular x1'),
(6, 11, 2, 1000000.00, 'pending', 2025-10-24 08:13:23, 'cake', 'cake@gmail.com', NULL, 'pending', 6, 'VIP x1'),
(7, 11, 2, 1000000.00, 'pending', 2025-10-24 08:13:37, 'cake', 'cake@gmail.com', NULL, 'pending', 7, 'VIP x1'),
(8, 11, 2, 1000000.00, 'pending', 2025-10-24 08:15:51, 'cake', 'cake@gmail.com', NULL, 'pending', 8, 'VIP x1'),
(9, 11, 2, 1000000.00, 'pending', 2025-10-24 08:16:03, 'cake', 'cake@gmail.com', NULL, 'pending', 9, 'VIP x1'),
(10, 11, 2, 1000000.00, 'pending', 2025-10-24 08:35:15, 'cake', 'cake@gmail.com', NULL, 'pending', 10, 'VIP x1'),
(11, 11, 2, 1000000.00, 'pending', 2025-10-24 08:46:55, 'cake', 'cake@gmail.com', NULL, 'pending', 11, 'VIP x1'),
(12, 11, 2, 100000.00, 'pending', 2025-10-24 08:48:22, 'cake', 'cake@gmail.com', NULL, 'pending', 12, 'Regular x1'),
(13, 11, 2, 100000.00, 'pending', 2025-10-24 08:56:25, 'cake', 'cake@gmail.com', NULL, 'paid', 13, 'Regular x1'),
(14, 11, 2, 100000.00, 'pending', 2025-10-24 09:08:34, 'cake', 'cake@gmail.com', NULL, 'paid', 14, 'Regular x1'),
(15, 11, 2, 1000000.00, 'pending', 2025-10-24 09:08:55, 'cake', 'cake@gmail.com', NULL, 'paid', 15, 'VIP x1'),
(16, 11, 2, 100000.00, 'pending', 2025-10-24 09:12:36, 'cake', 'cake@gmail.com', NULL, 'paid', 16, 'Regular x1'),
(17, 11, 2, 1000000.00, 'pending', 2025-10-24 09:24:41, 'cake', 'cake@gmail.com', NULL, 'paid', 17, 'VIP x1'),
(19, 11, 2, 100000.00, 'pending', 2025-11-06 13:39:31, 'cake', 'cake@gmail.com', NULL, 'paid', 19, 'Regular x1'),
(20, 11, 2, 100000.00, 'pending', 2025-11-06 15:44:37, 'cake', 'cake@gmail.com', NULL, 'paid', 20, 'Regular x1'),
(22, 11, 2, 1000000.00, 'pending', 2025-11-06 15:51:33, 'cake', 'cake@gmail.com', NULL, 'paid', 22, 'VIP x1'),
(23, 11, 2, 100000.00, 'pending', 2025-11-06 15:56:38, 'cake', 'cake@gmail.com', NULL, 'paid', 23, 'Regular x1'),
(25, 11, 2, 1000000.00, 'pending', 2025-11-06 16:29:33, 'cake', 'cake@gmail.com', NULL, 'paid', 25, 'VIP x1'),
(26, 11, 2, 100000.00, 'pending', 2025-11-06 16:30:21, 'cake', 'cake@gmail.com', NULL, 'paid', 26, 'Regular x1'),
(28, 11, 2, 100000.00, 'pending', 2025-11-06 21:58:39, 'cake', 'cake@gmail.com', NULL, 'paid', 28, 'Regular x1'),
(29, 11, 2, 100000.00, 'pending', 2025-11-06 22:17:34, 'cake', 'cake@gmail.com', NULL, 'paid', 29, 'Regular x1'),
(30, 11, 2, 100000.00, 'pending', 2025-11-06 22:30:41, 'cake', 'cake@gmail.com', NULL, 'paid', 30, 'Regular x1');

SET FOREIGN_KEY_CHECKS=1;
-- Backup completed
