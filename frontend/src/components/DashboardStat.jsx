import { motion } from "framer-motion";

export function DashboardStat({ label, value, icon: Icon, detail }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel rounded-panel p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
        </div>
        {Icon ? (
          <div className="grid h-10 w-10 place-items-center rounded-md border border-sky-400/20 bg-sky-400/10 text-sky-200">
            <Icon size={19} />
          </div>
        ) : null}
      </div>
      {detail ? <p className="mt-3 truncate text-xs text-slate-400">{detail}</p> : null}
    </motion.div>
  );
}
