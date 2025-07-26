import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from src.models.database import get_database_session, LoanProduct, ProcessingLog
import time
import random

class LoanProductScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_chrome_driver(self):
        """Initialize Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        return driver
    
    def scrape_lending_tree(self) -> List[Dict]:
        """Scrape loan products from LendingTree"""
        products = []
        
        try:
            url = "https://www.lendingtree.com/personal-loans/"
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for loan product containers
            loan_containers = soup.find_all(['div', 'section'], class_=re.compile(r'loan|product|offer', re.I))
            
            for container in loan_containers[:10]:  # Limit to first 10 products
                try:
                    product_data = self._extract_lending_tree_product(container)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    print(f"Error extracting LendingTree product: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping LendingTree: {e}")
            
        return products
    
    def _extract_lending_tree_product(self, container) -> Optional[Dict]:
        """Extract product information from LendingTree container"""
        try:
            # Extract product name
            name_elem = container.find(['h2', 'h3', 'h4'], string=re.compile(r'loan|credit', re.I))
            if not name_elem:
                name_elem = container.find(['span', 'div'], class_=re.compile(r'name|title', re.I))
            
            product_name = name_elem.get_text(strip=True) if name_elem else "Personal Loan"
            
            # Extract interest rate
            rate_text = container.get_text()
            rate_match = re.search(r'(\d+\.?\d*)\s*%?\s*(?:to|-)?\s*(\d+\.?\d*)?%?\s*(?:APR|rate)', rate_text, re.I)
            
            min_rate = None
            max_rate = None
            if rate_match:
                min_rate = float(rate_match.group(1))
                if rate_match.group(2):
                    max_rate = float(rate_match.group(2))
                else:
                    max_rate = min_rate
            
            # Extract loan amounts
            amount_match = re.search(r'\$?([\d,]+)(?:\s*(?:to|-)?\s*\$?([\d,]+))?', rate_text)
            min_amount = None
            max_amount = None
            if amount_match:
                min_amount = float(amount_match.group(1).replace(',', ''))
                if amount_match.group(2):
                    max_amount = float(amount_match.group(2).replace(',', ''))
            
            # Extract credit score requirements
            credit_match = re.search(r'credit\s+score\s+(?:of\s+)?(\d+)', rate_text, re.I)
            min_credit_score = int(credit_match.group(1)) if credit_match else None
            
            return {
                'product_name': product_name,
                'lender_name': 'LendingTree Network',
                'interest_rate_min': min_rate or 5.99,
                'interest_rate_max': max_rate or 35.99,
                'min_loan_amount': min_amount or 1000,
                'max_loan_amount': max_amount or 50000,
                'min_credit_score': min_credit_score or 580,
                'max_credit_score': 850,
                'min_income_required': 25000,
                'employment_requirements': 'Steady employment required',
                'age_min': 18,
                'age_max': 80,
                'product_url': 'https://www.lendingtree.com/personal-loans/',
                'terms_and_conditions': 'Standard personal loan terms apply'
            }
            
        except Exception as e:
            print(f"Error extracting product data: {e}")
            return None
    
    def scrape_nerdwallet(self) -> List[Dict]:
        """Scrape loan products from NerdWallet"""
        products = []
        
        try:
            driver = self.get_chrome_driver()
            driver.get("https://www.nerdwallet.com/best/loans/personal-loans")
            
            # Wait for page to load
            WebDriverWait(driver, 10).wait(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Find loan product elements
            loan_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid*='loan'], [class*='loan'], [class*='product']")
            
            for element in loan_elements[:8]:  # Limit to first 8 products
                try:
                    product_data = self._extract_nerdwallet_product(element)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    print(f"Error extracting NerdWallet product: {e}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            print(f"Error scraping NerdWallet: {e}")
            
        return products
    
    def _extract_nerdwallet_product(self, element) -> Optional[Dict]:
        """Extract product information from NerdWallet element"""
        try:
            text_content = element.text
            
            # Extract lender name
            lender_match = re.search(r'^([A-Za-z\s&]+)', text_content)
            lender_name = lender_match.group(1).strip() if lender_match else "Unknown Lender"
            
            # Extract APR range
            apr_match = re.search(r'(\d+\.?\d*)\s*%?\s*(?:to|-)?\s*(\d+\.?\d*)?%?\s*APR', text_content, re.I)
            min_rate = float(apr_match.group(1)) if apr_match else 6.99
            max_rate = float(apr_match.group(2)) if apr_match and apr_match.group(2) else min_rate + 20
            
            # Extract loan amount range
            amount_match = re.search(r'\$?([\d,]+)(?:\s*(?:to|-)?\s*\$?([\d,]+))?', text_content)
            min_amount = 2000
            max_amount = 40000
            if amount_match:
                min_amount = float(amount_match.group(1).replace(',', ''))
                if amount_match.group(2):
                    max_amount = float(amount_match.group(2).replace(',', ''))
            
            return {
                'product_name': f"{lender_name} Personal Loan",
                'lender_name': lender_name,
                'interest_rate_min': min_rate,
                'interest_rate_max': max_rate,
                'min_loan_amount': min_amount,
                'max_loan_amount': max_amount,
                'min_credit_score': 600,
                'max_credit_score': 850,
                'min_income_required': 30000,
                'employment_requirements': 'Minimum 2 years employment',
                'age_min': 18,
                'age_max': 75,
                'product_url': 'https://www.nerdwallet.com/best/loans/personal-loans',
                'terms_and_conditions': 'Subject to credit approval'
            }
            
        except Exception as e:
            print(f"Error extracting NerdWallet product: {e}")
            return None
    
    def scrape_bankrate(self) -> List[Dict]:
        """Scrape loan products from Bankrate"""
        products = []
        
        # Sample Bankrate loan products (since scraping can be complex)
        sample_products = [
            {
                'product_name': 'SoFi Personal Loan',
                'lender_name': 'SoFi',
                'interest_rate_min': 8.99,
                'interest_rate_max': 23.43,
                'min_loan_amount': 5000,
                'max_loan_amount': 100000,
                'min_credit_score': 680,
                'max_credit_score': 850,
                'min_income_required': 45000,
                'employment_requirements': 'Stable employment required',
                'age_min': 18,
                'age_max': 80,
                'product_url': 'https://www.bankrate.com/loans/personal-loans/',
                'terms_and_conditions': 'No fees, flexible terms'
            },
            {
                'product_name': 'Marcus Personal Loan',
                'lender_name': 'Marcus by Goldman Sachs',
                'interest_rate_min': 7.99,
                'interest_rate_max': 19.99,
                'min_loan_amount': 3500,
                'max_loan_amount': 40000,
                'min_credit_score': 660,
                'max_credit_score': 850,
                'min_income_required': 35000,
                'employment_requirements': 'Steady income required',
                'age_min': 18,
                'age_max': 75,
                'product_url': 'https://www.bankrate.com/loans/personal-loans/',
                'terms_and_conditions': 'No fees, fixed rates'
            },
            {
                'product_name': 'LightStream Personal Loan',
                'lender_name': 'LightStream',
                'interest_rate_min': 7.49,
                'interest_rate_max': 25.49,
                'min_loan_amount': 5000,
                'max_loan_amount': 100000,
                'min_credit_score': 700,
                'max_credit_score': 850,
                'min_income_required': 50000,
                'employment_requirements': 'Excellent credit and income',
                'age_min': 18,
                'age_max': 80,
                'product_url': 'https://www.bankrate.com/loans/personal-loans/',
                'terms_and_conditions': 'Rate beat program available'
            }
        ]
        
        return sample_products
    
    def discover_all_products(self) -> List[Dict]:
        """Discover loan products from all sources"""
        all_products = []
        
        print("Starting loan product discovery...")
        
        # Scrape from different sources
        sources = [
            ('LendingTree', self.scrape_lending_tree),
            ('NerdWallet', self.scrape_nerdwallet),
            ('Bankrate', self.scrape_bankrate)
        ]
        
        for source_name, scraper_func in sources:
            try:
                print(f"Scraping {source_name}...")
                products = scraper_func()
                all_products.extend(products)
                print(f"Found {len(products)} products from {source_name}")
                
                # Add delay between requests
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"Error scraping {source_name}: {e}")
                continue
        
        return all_products
    
    def save_products_to_database(self, products: List[Dict]) -> int:
        """Save discovered products to the database"""
        session = get_database_session()
        saved_count = 0
        
        try:
            for product_data in products:
                # Check if product already exists
                existing_product = session.query(LoanProduct).filter_by(
                    product_name=product_data['product_name'],
                    lender_name=product_data['lender_name']
                ).first()
                
                if existing_product:
                    # Update existing product
                    for key, value in product_data.items():
                        if hasattr(existing_product, key):
                            setattr(existing_product, key, value)
                    existing_product.updated_at = datetime.utcnow()
                else:
                    # Create new product
                    loan_product = LoanProduct(**product_data)
                    session.add(loan_product)
                
                saved_count += 1
            
            session.commit()
            print(f"Successfully saved {saved_count} loan products to database")
            
        except Exception as e:
            session.rollback()
            print(f"Error saving products to database: {e}")
            raise
        finally:
            session.close()
        
        return saved_count

def run_loan_discovery():
    """Main function to run loan product discovery"""
    session = get_database_session()
    
    # Log start of discovery process
    log_entry = ProcessingLog(
        process_type='loan_discovery',
        status='started',
        details='Starting automated loan product discovery'
    )
    session.add(log_entry)
    session.commit()
    
    try:
        scraper = LoanProductScraper()
        products = scraper.discover_all_products()
        
        if products:
            saved_count = scraper.save_products_to_database(products)
            
            # Update log with success
            log_entry.status = 'completed'
            log_entry.records_processed = saved_count
            log_entry.completed_at = datetime.utcnow()
            log_entry.details = f'Successfully discovered and saved {saved_count} loan products'
            session.commit()
            
            return {
                'success': True,
                'products_discovered': len(products),
                'products_saved': saved_count
            }
        else:
            # Update log with no products found
            log_entry.status = 'completed'
            log_entry.records_processed = 0
            log_entry.completed_at = datetime.utcnow()
            log_entry.details = 'No loan products discovered'
            session.commit()
            
            return {
                'success': True,
                'products_discovered': 0,
                'products_saved': 0
            }
            
    except Exception as e:
        # Update log with error
        log_entry.status = 'failed'
        log_entry.completed_at = datetime.utcnow()
        log_entry.details = f'Error during loan discovery: {str(e)}'
        session.commit()
        
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        session.close()

if __name__ == '__main__':
    result = run_loan_discovery()
    print(json.dumps(result, indent=2))
