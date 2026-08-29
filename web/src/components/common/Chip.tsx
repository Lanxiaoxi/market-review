import styles from "./Chip.module.css";

interface ChipProps {
  text: string;
  dotColor?: string;
}

export default function Chip({ text, dotColor }: ChipProps) {
  return (
    <span className={styles.chip}>
      <span className={styles.dot} style={dotColor ? { background: dotColor } : undefined} />
      <span className={styles.text}>{text}</span>
    </span>
  );
}