<script lang="ts">
  import type { Keepsake } from "../behavior/keepsakes";
  let { item, ending }: { item: Keepsake; ending: number } = $props();
</script>

<div class="find" class:throwing={ending === 2} class:stowing={ending === 0}>
  <img alt="" src={"data:image/png;base64," + item.icon} />{item.name}
</div>
{#if ending === 2}<span class="bin">🗑</span>{/if}

<style>
  .find,
  .bin {
    pointer-events: none;
  }
  .find {
    background: #fff0c5;
    color: #203047;
    padding: 6px;
    border-radius: 5px;
    font: 12px system-ui;
    box-shadow: 0 2px 5px #13243b55;
  }
  .find {
    position: absolute;
    width: max-content;
    max-width: 118px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    animation: inspect 4s both;
    /* Находка в руках, а не у кармана: сдвиг задаёт keepsakeScene (`--hands`). */
    margin-top: var(--hands, 0px);
  }
  img {
    width: 18px;
    height: 18px;
    vertical-align: middle;
  }
  .bin {
    position: absolute;
    left: 38px;
    top: 24px;
    animation: reveal 4s both;
  }
  @keyframes inspect {
    0% {
      transform: translateY(12px) scale(0.4);
    }
    35% {
      transform: translateY(-24px) rotate(-12deg);
    }
    50% {
      transform: translateY(-20px) rotate(9deg);
    }
    70% {
      transform: translateY(-16px) rotate(-5deg);
    }
    100% {
      transform: translateY(12px) scale(0.5);
      opacity: 0;
    }
  }
  .throwing {
    animation-name: toss;
  }
  .stowing {
    animation-name: stow;
  }
  @keyframes toss {
    0%,
    60% {
      transform: translateY(-16px) rotate(-9deg);
    }
    80% {
      transform: translate(20px, -26px) rotate(32deg);
    }
    100% {
      transform: translate(40px, 25px) scale(0.2);
      opacity: 0;
    }
  }
  @keyframes stow {
    0%,
    60% {
      transform: translateY(-18px) rotate(8deg);
    }
    85% {
      transform: rotate(-12deg);
    }
    100% {
      transform: translateY(8px) scale(0.1);
      opacity: 0;
    }
  }
  @keyframes reveal {
    0%,
    62% {
      opacity: 0;
    }
    70%,
    100% {
      opacity: 1;
    }
  }
</style>
