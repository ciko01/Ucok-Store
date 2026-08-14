export interface Product {
  product_id: number
  name: string
  category: string
  price: number
  description: string
  available_stock: number
  custom_id: string
  has_variants: boolean
  is_active: boolean
  stock_source: string
  stock_config: string
}

export interface Variant {
  variant_id: number
  product_id: number
  name: string
  price: number
  custom_id: string
  available_stock: number
  stock_source: string
  stock_config: string
}

export interface VariantCreate {
  name: string
  price: number
  custom_id?: string
}

export interface User {
  user_id: number
  username: string | null
  full_name: string
  balance: number
  first_seen_at: string
  last_seen_at: string
}

export interface Transaction {
  transaction_id: number
  user_id: number
  description: string | null
  transaction_type: string
  amount: number
  created_at: string
}

export interface TopUpRequest {
  request_id: number
  user_id: number
  full_name: string
  username: string | null
  amount: number
  proof_file_id: string
  status: string
  created_at: string
}

export interface Bank {
  bank_id: number
  bank_name: string
  account_number: string
  account_holder: string
  notes: string
  is_active: boolean
}

export interface Stats {
  total_users: number
  total_transactions: number
  total_revenue: number
  total_products: number
  pending_topups: number
}

export interface RevenuePoint {
  date: string
  revenue: number
  transactions: number
}

export interface TopBuyer {
  rank: number
  full_name: string
  username: string | null
  total_spent: number
  total_purchases: number
}

export interface AdminLog {
  log_id: number
  admin_id: number
  admin_name: string
  action: string
  detail: string
  created_at: string
}
