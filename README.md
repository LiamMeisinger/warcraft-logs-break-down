# Warcraft Logs API Integration

This project is an interactive web app that leverages the Warcraft Logs API to retrieve and display 
raid data for World of Warcraft players. It’s designed to be flexible, allowing users to input specific 
raid IDs and dynamically select encounters, avoiding the need for hardcoded values. The project aims to 
provide insights into different raids and player performance in a user-friendly format.

## Features

- Raid Data Retrieval: Enter any raid ID to pull up relevant information, allowing for customization and reusability across different raid encounters.
- Encounter Selection: Choose from all available encounters dynamically, enhancing flexibility for different raid setups and data needs.
- Item Level Filtering: Automatically excludes gear items with an item level of 0, ensuring only valuable data is displayed.Features

## Tech Stack

- Backend: Python
- Web Framework: Flask
- API: Warcraft Logs API, integrated using GraphQL queries for efficient data retrieval

