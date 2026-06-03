export default function LoadingSpinner({ label = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="h-10 w-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      {label && <p className="mt-3 text-sm text-gray-500">{label}</p>}
    </div>
  );
}
