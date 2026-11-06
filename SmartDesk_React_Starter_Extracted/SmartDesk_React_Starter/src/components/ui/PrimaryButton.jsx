
export function PrimaryButton({ children, icon: Icon, onClick, variant = 'primary', size = 'md', className = '', ...props }) {
  const base = "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-desk-bg disabled:opacity-50 disabled:pointer-events-none";

  const variants = {
    primary: "bg-blue-600 hover:bg-blue-500 text-white shadow-sm focus:ring-blue-500",
    secondary: "bg-[#181c24] hover:bg-[#202634] text-slate-200 border border-slate-700/80 focus:ring-slate-500",
    danger: "bg-rose-600 hover:bg-rose-500 text-white focus:ring-rose-500",
    ai: "bg-purple-600 hover:bg-purple-500 text-white shadow-sm focus:ring-purple-500",
    ghost: "bg-transparent hover:bg-slate-800 text-slate-300 focus:ring-slate-600"
  };

  const sizes = {
    sm: "px-2.5 py-1.5 text-xs gap-1.5",
    md: "px-3.5 py-2 text-sm gap-2",
    lg: "px-4.5 py-2.5 text-base gap-2.5"
  };

  return (
    <button type="button" onClick={onClick} className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {Icon && <Icon className={size === 'sm' ? "w-3.5 h-3.5" : "w-4 h-4"} />}
      {children}
    </button>
  );
}
