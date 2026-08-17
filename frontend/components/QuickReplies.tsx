export function QuickReplies({
  options,
  disabled,
  onPick,
}: {
  options: string[];
  disabled: boolean;
  onPick: (option: string) => void;
}) {
  return (
    <div className="quick-replies" role="group" aria-label="Quick reply options">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          className="quick-reply-chip"
          disabled={disabled}
          onClick={() => onPick(option)}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
