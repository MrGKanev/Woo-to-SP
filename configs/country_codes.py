# configs/country_codes.py

COUNTRY_CODES = {
    # North America
    'UNITED STATES': 'US',
    'USA': 'US',
    'CANADA': 'CA',
    'MEXICO': 'MX',
    
    # Europe
    'UNITED KINGDOM': 'GB',
    'UK': 'GB',
    'GREAT BRITAIN': 'GB',
    'GERMANY': 'DE',
    'FRANCE': 'FR',
    'ITALY': 'IT',
    'SPAIN': 'ES',
    'NETHERLANDS': 'NL',
    'BELGIUM': 'BE',
    'SWITZERLAND': 'CH',
    'SWEDEN': 'SE',
    'NORWAY': 'NO',
    'DENMARK': 'DK',
    'FINLAND': 'FI',
    'IRELAND': 'IE',
    
    # Asia Pacific
    'AUSTRALIA': 'AU',
    'NEW ZEALAND': 'NZ',
    'JAPAN': 'JP',
    'CHINA': 'CN',
    'HONG KONG': 'HK',
    'SINGAPORE': 'SG',
    'SOUTH KOREA': 'KR',
    'KOREA': 'KR',
    'TAIWAN': 'TW',
    
    # Other common variations
    'UNITED STATES OF AMERICA': 'US',
    'U.S.A.': 'US',
    'U.S.': 'US',
    'ENGLAND': 'GB'
}

def get_country_code(country: str, default: str = 'US') -> str:
    """
    Convert country name to ISO 2-letter country code.
    
    Args:
        country: Country name or code
        default: Default country code to return if no match found (defaults to 'US')
    
    Returns:
        Two-letter country code
    """
    if not country:
        return default
        
    # Clean the input
    cleaned = country.strip().upper()
    
    # If it's already a valid 2-letter code, return it
    if len(cleaned) == 2:
        return cleaned
        
    # Look up in mapping
    return COUNTRY_CODES.get(cleaned, default)