-- Create database and switch to it
CREATE DATABASE IF NOT EXISTS microservices;
USE microservices;

-- Drop tables if they exist to start fresh
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    cash_balance DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0,
    category VARCHAR(50),
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'completed', 'cancelled') DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Insert users
-- --------------------------------------------------------
INSERT INTO `users` (`id`, `name`, `email`, `cash_balance`, `created_at`) VALUES
(1, 'Aarav Sharma', 'aarav.sharma@example.co.in', 50000.00, '2024-01-15 10:00:00'),
(2, 'Priya Patel', 'priya.patel@example.com', 75000.00, '2024-01-20 11:30:00'),
(3, 'Rohan Kumar', 'rohan.k@example.co.in', 12000.50, '2024-02-01 09:00:00'),
(4, 'Ananya Singh', 'ananya.s@example.com', 98000.75, '2024-02-10 14:00:00'),
(5, 'Vikram Joshi', 'vikram.joshi@example.in', 4500.00, '2024-02-22 18:00:00'),
(6, 'Isha Gupta', 'isha.gupta@example.com', 250000.00, '2024-03-05 12:00:00'),
(7, 'Arjun Reddy', 'arjun.reddy@example.co.in', 8900.25, '2024-03-15 16:45:00'),
(8, 'Mira Nair', 'mira.nair@example.com', 150000.00, '2024-04-02 20:00:00'),
(9, 'Kabir Khan', 'kabir.k@example.in', 7600.00, '2024-04-18 08:30:00'),
(10, 'Diya Mehta', 'diya.mehta@example.com', 42000.00, '2024-05-01 13:00:00'),
(11, 'Siddharth Roy', 'sid.roy@example.com', 62000.00, '2024-05-15 11:00:00'),
(12, 'Neha Agarwal', 'neha.a@example.co.in', 33000.50, '2024-06-02 14:20:00'),
(13, 'Raj Malhotra', 'raj.m@example.com', 89000.00, '2024-06-20 18:00:00'),
(14, 'Kavita Iyer', 'kavita.iyer@example.in', 5100.00, '2024-07-01 09:45:00');


-- --------------------------------------------------------
-- Insert products
-- --------------------------------------------------------
INSERT INTO `products` (`id`, `name`, `description`, `price`, `stock`, `category`, `image_url`) VALUES
(1, 'OnePlus Nord CE 4 (128GB)', '8GB RAM, Celadon Marble, 5G Smartphone', 24999.00, 50, 'Electronics', 'https://m.media-amazon.com/images/I/61o6gS-I60L._AC_SL1500_.jpg'),
(2, 'Samsung Galaxy M34 5G', '6GB, 128GB Storage, Prism Silver', 15999.00, 75, 'Electronics', 'https://m.media-amazon.com/images/I/816s52soBwL._AC_SL1500_.jpg'),
(3, 'boAt Airdopes 141', 'ANC TWS Earbuds with 42H Playtime', 1299.00, 200, 'Electronics', 'https://m.media-amazon.com/images/I/51-v42jA25L._AC_SL1500_.jpg'),
(4, 'The Psychology of Money', 'Paperback by Morgan Housel', 350.00, 150, 'Books', NULL),
(5, 'Atomic Habits', 'Paperback by James Clear', 499.00, 250, 'Books', NULL),
(6, 'Men\'s Cotton T-Shirt', 'Solid color, regular fit', 599.00, 300, 'Clothing', NULL),
(7, 'Women\'s Kurta Set', 'Printed cotton with palazzo', 1499.00, 120, 'Clothing', NULL),
(8, 'Prestige Pressure Cooker', '5 Litre, Aluminium', 1800.00, 80, 'Home & Kitchen', NULL),
(9, 'Milton Water Bottle', '1 Litre, Stainless Steel', 750.00, 400, 'Home & Kitchen', NULL),
(10, 'Aashirvaad Atta', '5kg pack of whole wheat flour', 250.00, 500, 'Groceries', NULL),
(11, 'Tata Salt', '1kg pack, Iodized', 25.00, 1000, 'Groceries', NULL),
(12, 'Dell Inspiron 15 Laptop', 'Intel Core i5, 8GB RAM, 512GB SSD', 55000.00, 40, 'Electronics', NULL),
(13, 'Sony Bravia 43" TV', 'Full HD Smart LED TV', 42999.00, 30, 'Electronics', NULL),
(14, 'Levi\'s 511 Jeans', 'Slim fit, dark wash denim', 2999.00, 90, 'Clothing', NULL);


-- --------------------------------------------------------
-- Insert orders
-- --------------------------------------------------------
INSERT INTO `orders` (`id`, `user_id`, `product_id`, `quantity`, `total_price`, `status`, `created_at`) VALUES
(1, 1, 3, 2, 2598.00, 'completed', '2024-05-10 08:30:00'),
(2, 2, 1, 1, 24999.00, 'completed', '2024-05-11 12:00:00'),
(3, 3, 2, 1, 15999.00, 'pending', '2024-05-12 15:45:00'),
(4, 4, 5, 1, 499.00, 'completed', '2024-06-01 10:00:00'),
(5, 5, 10, 5, 1250.00, 'completed', '2024-06-03 11:30:00'),
(6, 6, 13, 1, 42999.00, 'completed', '2024-06-05 09:00:00'),
(7, 7, 6, 3, 1797.00, 'cancelled', '2024-06-10 14:00:00'),
(8, 8, 8, 1, 1800.00, 'completed', '2024-06-15 18:00:00'),
(9, 9, 11, 10, 250.00, 'pending', '2024-06-22 12:00:00'),
(10, 10, 4, 2, 700.00, 'completed', '2024-07-01 16:45:00'),
(11, 1, 12, 1, 55000.00, 'completed', '2024-07-05 20:00:00'),
(12, 2, 7, 1, 1499.00, 'completed', '2024-07-10 08:30:00'),
(13, 11, 9, 4, 3000.00, 'pending', '2024-07-18 13:00:00'),
(14, 12, 14, 1, 2999.00, 'cancelled', '2024-07-25 10:00:00'),
(15, 13, 4, 1, 350.00, 'completed', '2024-08-01 11:00:00'),
(16, 14, 6, 2, 1198.00, 'completed', '2024-08-05 15:30:00'),
(17, 3, 11, 20, 500.00, 'completed', '2024-08-10 09:15:00'),
(18, 5, 3, 1, 1299.00, 'pending', '2024-08-12 14:00:00'),
(19, 8, 1, 1, 24999.00, 'completed', '2024-08-18 19:00:00'),
(20, 1, 5, 1, 499.00, 'completed', '2024-08-20 12:00:00'),
(21, 6, 14, 1, 2999.00, 'cancelled', '2024-08-25 16:00:00'),
(22, 10, 8, 1, 1800.00, 'completed', '2024-09-01 10:30:00'),
(23, 12, 10, 3, 750.00, 'pending', '2024-09-03 11:45:00'),
(24, 4, 2, 1, 15999.00, 'completed', '2024-09-05 17:00:00');